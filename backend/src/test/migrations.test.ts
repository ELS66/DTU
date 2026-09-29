import assert from 'node:assert/strict';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import type { PoolClient } from 'pg';
import { loadMigrations, pendingMigrations, runMigrations } from '../db/migrations.js';
import { bootstrapTenant } from '../db/bootstrap.js';

const files = loadMigrations(fileURLToPath(new URL('../../migrations/', import.meta.url)));

test('migration files are consecutive and checksum changes are rejected', () => {
  assert.deepEqual(files.map((file) => file.version), [1, 2, 3]);
  assert.equal(pendingMigrations(files, []).length, 3);
  assert.equal(pendingMigrations(files, files.slice(0, 2)).length, 1);
  assert.equal(pendingMigrations(files, files).length, 0);
  assert.throws(() => pendingMigrations(files, [{ ...files[0]!, checksum: '0'.repeat(64) }]));
  assert.throws(() => pendingMigrations(files, [files[1]!]));
});

test('migration runner commits together and rolls back on a failed SQL script', async () => {
  const queries: string[] = [];
  const client = { query: async (sql: string) => {
    queries.push(sql);
    if (sql.startsWith('SELECT version')) return { rows: [] };
    if (sql === files[1]!.sql) throw new Error('SQL failed');
    return { rows: [] };
  } } as unknown as PoolClient;
  await assert.rejects(runMigrations(client, files), /SQL failed/);
  assert.equal(queries[0], 'BEGIN');
  assert.equal(queries.at(-1), 'ROLLBACK');
  assert.equal(queries.includes('COMMIT'), false);
});

test('bootstrap creates one tenant administrator transactionally and refuses a second run', async () => {
  const queries: string[] = [];
  const client = { query: async (sql: string) => {
    queries.push(sql);
    if (sql.startsWith('SELECT EXISTS')) return { rows: [{ has_users: false, has_tenants: false }] };
    return { rows: [] };
  } } as unknown as PoolClient;
  const ids = await bootstrapTenant(client, 'admin', 'Sample tenant', 'strong bootstrap password');
  assert.match(ids.userId, /^[0-9a-f-]{36}$/);
  assert.equal(queries.at(-1), 'COMMIT');
  const blocked = { query: async (sql: string) => {
    queries.push(sql);
    if (sql.startsWith('SELECT EXISTS')) return { rows: [{ has_users: true, has_tenants: true }] };
    return { rows: [] };
  } } as unknown as PoolClient;
  await assert.rejects(bootstrapTenant(blocked, 'admin', 'Sample tenant', 'strong bootstrap password'),
    /empty user and tenant database/);
  assert.equal(queries.at(-1), 'ROLLBACK');
});
