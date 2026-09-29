import type { Pool } from 'pg';
import type { AuthStore, AuthenticatedUser, Membership, ProjectSummary, TenantRole, UserRecord } from './store.js';

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

  async listProjects(tenantId: string, userId: string, role: TenantRole): Promise<ProjectSummary[]> {
    const result = await this.pool.query<ProjectSummary>(
      `SELECT p.id, p.name FROM project p WHERE p.tenant_id = $1
       AND ($3 = 'TENANT_ADMIN' OR EXISTS (
         SELECT 1 FROM project_member pm WHERE pm.tenant_id = p.tenant_id
         AND pm.project_id = p.id AND pm.user_id = $2
       )) ORDER BY p.name, p.id`,
      [tenantId, userId, role],
    );
    return result.rows;
  }
}
