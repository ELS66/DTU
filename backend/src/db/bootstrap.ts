import { randomUUID } from 'node:crypto';
import type { PoolClient } from 'pg';
import { hashPassword } from '../auth/password.js';

export async function bootstrapTenant(client: PoolClient, loginName: string,
                                      tenantName: string, password: string): Promise<{
  userId: string; tenantId: string;
}> {
  if (!/^[A-Za-z0-9_.@-]{3,120}$/.test(loginName)) {
    throw new Error('login name must be 3..120 ASCII letters, digits or ._@-');
  }
  if (!tenantName.trim() || tenantName.length > 160) {
    throw new Error('tenant name must be 1..160 characters');
  }
  const passwordHash = await hashPassword(password);
  await client.query('BEGIN');
  try {
    await client.query('SELECT pg_advisory_xact_lock(498231022)');
    const existing = await client.query<{ has_users: boolean; has_tenants: boolean }>(
      'SELECT EXISTS(SELECT 1 FROM app_user) AS has_users, EXISTS(SELECT 1 FROM tenant) AS has_tenants',
    );
    if (existing.rows[0]?.has_users || existing.rows[0]?.has_tenants) {
      throw new Error('bootstrap requires an empty user and tenant database');
    }
    const userId = randomUUID();
    const tenantId = randomUUID();
    await client.query('INSERT INTO app_user (id, login_name, password_hash) VALUES ($1, $2, $3)',
      [userId, loginName, passwordHash]);
    await client.query('INSERT INTO tenant (id, name) VALUES ($1, $2)', [tenantId, tenantName.trim()]);
    await client.query("INSERT INTO tenant_member (tenant_id, user_id, role) VALUES ($1, $2, 'TENANT_ADMIN')",
      [tenantId, userId]);
    await client.query('COMMIT');
    return { userId, tenantId };
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}
