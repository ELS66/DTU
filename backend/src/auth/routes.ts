import { createHash, randomBytes } from 'node:crypto';
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { hashPassword, verifyPassword } from './password.js';
import type { AuthenticatedUser, AuthStore } from './store.js';

const SESSION_MS = 12 * 60 * 60 * 1000;
const dummyHash = hashPassword('not-a-real-user-password');
const tokenHash = (token: string) => createHash('sha256').update(token).digest('hex');

async function authenticate(request: FastifyRequest, store: AuthStore): Promise<{
  user: AuthenticatedUser; hash: string;
} | null> {
  const match = /^Bearer ([A-Za-z0-9_-]{43})$/.exec(request.headers.authorization ?? '');
  if (!match) return null;
  const hash = tokenHash(match[1]!);
  const user = await store.findActiveSession(hash, new Date());
  return user ? { user, hash } : null;
}

export function registerAuthRoutes(app: FastifyInstance, store: AuthStore): void {
  app.post('/api/v1/auth/login', {
    schema: { body: {
      type: 'object', additionalProperties: false, required: ['loginName', 'password'],
      properties: {
        loginName: { type: 'string', minLength: 1, maxLength: 120 },
        password: { type: 'string', minLength: 1, maxLength: 1024 },
      },
    } },
  }, async (request, reply) => {
    const body = request.body as { loginName: string; password: string };
    const record = await store.findUserByLogin(body.loginName);
    const valid = await verifyPassword(body.password, record?.passwordHash ?? await dummyHash);
    if (!record?.enabled || !valid) {
      return reply.code(401).send({ code: 'INVALID_CREDENTIALS' });
    }
    const token = randomBytes(32).toString('base64url');
    const expiresAt = new Date(Date.now() + SESSION_MS);
    await store.createSession(tokenHash(token), record.id, expiresAt);
    reply.header('Cache-Control', 'no-store');
    return { accessToken: token, tokenType: 'Bearer', expiresAt: expiresAt.toISOString() };
  });

  app.post('/api/v1/auth/logout', async (request, reply) => {
    const session = await authenticate(request, store);
    if (!session) return reply.code(401).send({ code: 'UNAUTHORIZED' });
    await store.revokeSession(session.hash);
    return reply.code(204).send();
  });

  app.get('/api/v1/me', async (request, reply) => {
    const session = await authenticate(request, store);
    if (!session) return reply.code(401).send({ code: 'UNAUTHORIZED' });
    reply.header('Cache-Control', 'no-store');
    return { id: session.user.id, loginName: session.user.loginName,
      tenants: await store.listMemberships(session.user.id) };
  });

  app.get('/api/v1/tenants/:tenantId/projects', {
    schema: { params: { type: 'object', required: ['tenantId'], properties: {
      tenantId: { type: 'string', pattern: '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' },
    } } },
  }, async (request, reply) => {
    const session = await authenticate(request, store);
    if (!session) return reply.code(401).send({ code: 'UNAUTHORIZED' });
    const { tenantId } = request.params as { tenantId: string };
    const role = await store.findTenantRole(session.user.id, tenantId);
    if (!role) return reply.code(404).send({ code: 'NOT_FOUND' });
    reply.header('Cache-Control', 'no-store');
    return { items: await store.listProjects(tenantId, session.user.id, role) };
  });
}
