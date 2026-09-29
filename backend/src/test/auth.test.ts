import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createApp } from '../app.js';
import { hashPassword, verifyPassword } from '../auth/password.js';
import type { AuthStore, AuthenticatedUser, Membership, ProjectSummary, TenantRole, UserRecord } from '../auth/store.js';

const ALPHA = 'aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa';
const BETA = 'bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb';
const USER = '11111111-1111-4111-8111-111111111111';
const OTHER = '22222222-2222-4222-8222-222222222222';

class MemoryAuthStore implements AuthStore {
  users = new Map<string, UserRecord>();
  sessions = new Map<string, { userId: string; expiresAt: Date; revoked: boolean }>();
  members = new Map<string, Membership[]>();
  projects = new Map<string, { id: string; name: string; memberIds: string[] }[]>();

  async findUserByLogin(name: string) { return this.users.get(name) ?? null; }
  async createSession(hash: string, userId: string, expiresAt: Date) {
    this.sessions.set(hash, { userId, expiresAt, revoked: false });
  }
  async findActiveSession(hash: string, now: Date): Promise<AuthenticatedUser | null> {
    const session = this.sessions.get(hash);
    if (!session || session.revoked || session.expiresAt <= now) return null;
    const user = [...this.users.values()].find((item) => item.id === session.userId && item.enabled);
    return user ? { id: user.id, loginName: user.loginName } : null;
  }
  async revokeSession(hash: string) {
    const session = this.sessions.get(hash);
    if (session) session.revoked = true;
  }
  async listMemberships(userId: string) { return this.members.get(userId) ?? []; }
  async findTenantRole(userId: string, tenantId: string): Promise<TenantRole | null> {
    return this.members.get(userId)?.find((membership) => membership.tenantId === tenantId)?.role ?? null;
  }
  async listProjects(tenantId: string, userId: string, role: TenantRole): Promise<ProjectSummary[]> {
    return (this.projects.get(tenantId) ?? []).filter((project) => role === 'TENANT_ADMIN'
      || project.memberIds.includes(userId)).map(({ id, name }) => ({ id, name }));
  }
}

test('password hashes verify without exposing the original password', async () => {
  const hash = await hashPassword('strong test password');
  assert.match(hash, /^scrypt\$/);
  assert.equal(await verifyPassword('strong test password', hash), true);
  assert.equal(await verifyPassword('wrong password', hash), false);
});

test('login, tenant isolation, project membership and logout', async () => {
  const store = new MemoryAuthStore();
  store.users.set('alice', { id: USER, loginName: 'alice', enabled: true,
    passwordHash: await hashPassword('correct horse battery staple') });
  store.users.set('bob', { id: OTHER, loginName: 'bob', enabled: true,
    passwordHash: await hashPassword('another strong password') });
  store.members.set(USER, [{ tenantId: ALPHA, tenantName: 'Alpha', role: 'USER' }]);
  store.members.set(OTHER, [{ tenantId: BETA, tenantName: 'Beta', role: 'TENANT_ADMIN' }]);
  store.projects.set(ALPHA, [
    { id: 'project-allowed', name: 'Allowed', memberIds: [USER] },
    { id: 'project-hidden', name: 'Hidden', memberIds: [] },
  ]);
  store.projects.set(BETA, [{ id: 'project-beta', name: 'Beta', memberIds: [] }]);
  const app = createApp({ authStore: store });
  try {
    const bad = await app.inject({ method: 'POST', url: '/api/v1/auth/login',
      payload: { loginName: 'alice', password: 'wrong' } });
    assert.equal(bad.statusCode, 401);
    const login = await app.inject({ method: 'POST', url: '/api/v1/auth/login',
      payload: { loginName: 'alice', password: 'correct horse battery staple' } });
    assert.equal(login.statusCode, 200);
    const token = login.json().accessToken as string;
    assert.equal(token.length, 43);
    const headers = { authorization: `Bearer ${token}` };
    const me = await app.inject({ method: 'GET', url: '/api/v1/me', headers });
    assert.equal(me.statusCode, 200);
    assert.deepEqual(me.json().tenants, [{ tenantId: ALPHA, tenantName: 'Alpha', role: 'USER' }]);
    const own = await app.inject({ method: 'GET', url: `/api/v1/tenants/${ALPHA}/projects`, headers });
    assert.deepEqual(own.json().items, [{ id: 'project-allowed', name: 'Allowed' }]);
    const foreign = await app.inject({ method: 'GET', url: `/api/v1/tenants/${BETA}/projects`, headers });
    assert.equal(foreign.statusCode, 404);
    store.members.set(USER, []);
    assert.equal((await app.inject({ method: 'GET', url: `/api/v1/tenants/${ALPHA}/projects`, headers })).statusCode, 404);
    store.members.set(USER, [{ tenantId: ALPHA, tenantName: 'Alpha', role: 'USER' }]);
    store.users.get('alice')!.enabled = false;
    assert.equal((await app.inject({ method: 'GET', url: '/api/v1/me', headers })).statusCode, 401);
    store.users.get('alice')!.enabled = true;
    const logout = await app.inject({ method: 'POST', url: '/api/v1/auth/logout', headers });
    assert.equal(logout.statusCode, 204);
    assert.equal((await app.inject({ method: 'GET', url: '/api/v1/me', headers })).statusCode, 401);
  } finally {
    await app.close();
  }
});
