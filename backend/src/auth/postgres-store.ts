import type { Pool } from 'pg';
import { randomUUID } from 'node:crypto';
import type { AuthStore, AuthenticatedUser, InvitationAcceptance, Membership, ProjectRole, ProjectSummary, TenantMemberSummary, TenantRole, UserRecord } from './store.js';

export class PostgresAuthStore implements AuthStore {
  constructor(private readonly pool: Pool) {}

  async findUserByLogin(loginName: string): Promise<UserRecord | null> {
    const result = await this.pool.query<{
      id: string; login_name: string; password_hash: string; enabled: boolean;
    }>('SELECT id, login_name, password_hash, enabled FROM app_user WHERE login_name = $1', [loginName]);
    const row = result.rows[0];
    return row ? { id: row.id, loginName: row.login_name, passwordHash: row.password_hash,
      enabled: row.enabled } : null;
  }

  async createSession(tokenHash: string, userId: string, expiresAt: Date): Promise<void> {
    await this.pool.query(
      'INSERT INTO auth_session (token_hash, user_id, expires_at) VALUES ($1, $2, $3)',
      [tokenHash, userId, expiresAt],
    );
  }

  async findActiveSession(tokenHash: string, now: Date): Promise<AuthenticatedUser | null> {
    const result = await this.pool.query<{ id: string; login_name: string }>(
      `SELECT u.id, u.login_name FROM auth_session s
       JOIN app_user u ON u.id = s.user_id
       WHERE s.token_hash = $1 AND s.revoked_at IS NULL AND s.expires_at > $2 AND u.enabled`,
      [tokenHash, now],
    );
    const row = result.rows[0];
    return row ? { id: row.id, loginName: row.login_name } : null;
  }

  async revokeSession(tokenHash: string): Promise<void> {
    await this.pool.query('UPDATE auth_session SET revoked_at = now() WHERE token_hash = $1 AND revoked_at IS NULL',
      [tokenHash]);
  }

  async listMemberships(userId: string): Promise<Membership[]> {
    const result = await this.pool.query<{
      tenant_id: string; name: string; role: TenantRole;
    }>(
      `SELECT m.tenant_id, t.name, m.role FROM tenant_member m
       JOIN tenant t ON t.id = m.tenant_id WHERE m.user_id = $1 ORDER BY t.name, t.id`,
      [userId],
    );
    return result.rows.map((row) => ({ tenantId: row.tenant_id, tenantName: row.name, role: row.role }));
  }

  async findTenantRole(userId: string, tenantId: string): Promise<TenantRole | null> {
    const result = await this.pool.query<{ role: TenantRole }>(
      'SELECT role FROM tenant_member WHERE tenant_id = $1 AND user_id = $2',
      [tenantId, userId],
    );
    return result.rows[0]?.role ?? null;
  }

  async listProjects(tenantId: string, userId: string): Promise<ProjectSummary[] | null> {
    const result = await this.pool.query<{ id: string | null; name: string | null }>(
      `SELECT p.id, p.name FROM tenant_member actor
       LEFT JOIN project p ON p.tenant_id = actor.tenant_id AND (
         actor.role = 'TENANT_ADMIN' OR EXISTS (
           SELECT 1 FROM project_member pm WHERE pm.tenant_id = p.tenant_id
             AND pm.project_id = p.id AND pm.user_id = actor.user_id
         )
       ) WHERE actor.tenant_id = $1 AND actor.user_id = $2 ORDER BY p.name, p.id`,
      [tenantId, userId],
    );
    return result.rows.length ? result.rows.filter((row): row is ProjectSummary =>
      row.id !== null && row.name !== null) : null;
  }

  async createProject(tenantId: string, actorId: string, projectId: string,
                      name: string): Promise<ProjectSummary | null> {
    const result = await this.pool.query<ProjectSummary>(
      `INSERT INTO project (id, tenant_id, name)
       SELECT $3, t.id, $4 FROM tenant t
       JOIN tenant_member actor ON actor.tenant_id = t.id
         AND actor.user_id = $2 AND actor.role = 'TENANT_ADMIN'
       WHERE t.id = $1 RETURNING id, name`,
      [tenantId, actorId, projectId, name],
    );
    return result.rows[0] ?? null;
  }

  async setProjectMember(tenantId: string, projectId: string, actorId: string,
                         memberId: string, role: ProjectRole): Promise<boolean> {
    const result = await this.pool.query(
      `INSERT INTO project_member (tenant_id, project_id, user_id, role)
       SELECT p.tenant_id, p.id, target.user_id, $5
       FROM project p
       JOIN tenant_member actor ON actor.tenant_id = p.tenant_id
         AND actor.user_id = $3 AND actor.role = 'TENANT_ADMIN'
       JOIN tenant_member target ON target.tenant_id = p.tenant_id AND target.user_id = $4
       WHERE p.tenant_id = $1 AND p.id = $2
       ON CONFLICT (project_id, user_id) DO UPDATE SET role = EXCLUDED.role
       RETURNING user_id`,
      [tenantId, projectId, actorId, memberId, role],
    );
    return (result.rowCount ?? 0) === 1;
  }

  async listTenantMembers(tenantId: string, actorId: string): Promise<TenantMemberSummary[] | null> {
    const result = await this.pool.query<{ id: string; login_name: string; role: TenantRole }>(
      `SELECT u.id, u.login_name, member.role FROM tenant_member member
       JOIN app_user u ON u.id = member.user_id
       WHERE member.tenant_id = $1 AND EXISTS (
         SELECT 1 FROM tenant_member actor WHERE actor.tenant_id = member.tenant_id
           AND actor.user_id = $2 AND actor.role = 'TENANT_ADMIN'
       ) ORDER BY u.login_name, u.id`,
      [tenantId, actorId],
    );
    return result.rows.length ? result.rows.map((row) => ({ id: row.id,
      loginName: row.login_name, role: row.role })) : null;
  }

  async createInvitation(tenantId: string, actorId: string, invitationId: string,
                         loginName: string, role: TenantRole, tokenHash: string,
                         expiresAt: Date): Promise<boolean> {
    const result = await this.pool.query(
      `INSERT INTO tenant_invitation
         (id, tenant_id, login_name, role, token_hash, invited_by, expires_at)
       SELECT $3, actor.tenant_id, $4, $5, $6, actor.user_id, $7
       FROM tenant_member actor
       WHERE actor.tenant_id = $1 AND actor.user_id = $2 AND actor.role = 'TENANT_ADMIN'
         AND NOT EXISTS (SELECT 1 FROM app_user WHERE login_name = $4)
       RETURNING id`,
      [tenantId, actorId, invitationId, loginName, role, tokenHash, expiresAt],
    );
    return (result.rowCount ?? 0) === 1;
  }

  async isInvitationActive(tokenHash: string): Promise<boolean> {
    const result = await this.pool.query<{ active: boolean }>(
      `SELECT EXISTS(SELECT 1 FROM tenant_invitation WHERE token_hash = $1
       AND consumed_at IS NULL AND expires_at > now()) AS active`, [tokenHash],
    );
    return result.rows[0]?.active ?? false;
  }

  async acceptInvitation(tokenHash: string, passwordHash: string): Promise<InvitationAcceptance> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      try {
        const result = await client.query<{
          id: string; tenant_id: string; login_name: string; role: TenantRole;
        }>(
          `SELECT id, tenant_id, login_name, role FROM tenant_invitation
           WHERE token_hash = $1 AND consumed_at IS NULL AND expires_at > now() FOR UPDATE`,
          [tokenHash],
        );
        const invitation = result.rows[0];
        if (!invitation) {
          await client.query('ROLLBACK');
          return 'INVALID';
        }
        const userId = randomUUID();
        await client.query('INSERT INTO app_user (id, login_name, password_hash) VALUES ($1, $2, $3)',
          [userId, invitation.login_name, passwordHash]);
        await client.query('INSERT INTO tenant_member (tenant_id, user_id, role) VALUES ($1, $2, $3)',
          [invitation.tenant_id, userId, invitation.role]);
        await client.query('UPDATE tenant_invitation SET consumed_at = now() WHERE id = $1',
          [invitation.id]);
        await client.query('COMMIT');
        return { userId, tenantId: invitation.tenant_id, loginName: invitation.login_name };
      } catch (error) {
        await client.query('ROLLBACK');
        if ((error as { code?: string }).code === '23505') return 'LOGIN_EXISTS';
        throw error;
      }
    } finally {
      client.release();
    }
  }
}
