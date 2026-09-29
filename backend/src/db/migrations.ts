import { createHash } from 'node:crypto';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import type { PoolClient } from 'pg';

export interface Migration {
  version: number;
  name: string;
  checksum: string;
  sql: string;
}

export interface AppliedMigration {
  version: number;
  name: string;
  checksum: string;
}

export function loadMigrations(directory: string): Migration[] {
  const migrations = readdirSync(directory).filter((name) => name.endsWith('.sql')).map((name) => {
    const match = /^V([1-9][0-9]*)__([A-Za-z0-9_]+)\.sql$/.exec(name);
    if (!match) throw new Error(`invalid migration filename: ${name}`);
    const sql = readFileSync(join(directory, name), 'utf8').replace(/\r\n/g, '\n');
    if (!sql.trim()) throw new Error(`empty migration: ${name}`);
    return { version: Number(match[1]), name,
      checksum: createHash('sha256').update(sql).digest('hex'), sql };
  }).sort((a, b) => a.version - b.version);
  if (migrations.length === 0) throw new Error('no migration files found');
  migrations.forEach((migration, index) => {
    if (!Number.isSafeInteger(migration.version) || migration.version !== index + 1) {
      throw new Error('migration versions must start at V1 and be consecutive');
    }
  });
  return migrations;
}

export function pendingMigrations(files: Migration[], applied: AppliedMigration[]): Migration[] {
  const known = new Map(files.map((migration) => [migration.version, migration]));
  for (const row of applied) {
    const file = known.get(row.version);
    if (!file || file.name !== row.name || file.checksum !== row.checksum.trim()) {
      throw new Error(`migration V${row.version} changed or is missing`);
    }
  }
  const appliedVersions = new Set(applied.map((row) => row.version));
  // Refuse a gap in the applied sequence rather than running a lower version after a higher one.
  for (let version = 1; version <= appliedVersions.size; version++) {
    if (!appliedVersions.has(version)) throw new Error('applied migration versions are not consecutive');
  }
  return files.filter((migration) => !appliedVersions.has(migration.version));
}

export async function runMigrations(client: PoolClient, files: Migration[]): Promise<number> {
  await client.query('BEGIN');
  try {
    await client.query('SELECT pg_advisory_xact_lock(498231021)');
    await client.query(`CREATE TABLE IF NOT EXISTS schema_migration (
      version integer PRIMARY KEY,
      name text NOT NULL,
      checksum char(64) NOT NULL,
      applied_at timestamptz NOT NULL DEFAULT now()
    )`);
    const existing = await client.query<AppliedMigration>(
      'SELECT version, name, checksum FROM schema_migration ORDER BY version',
    );
    const pending = pendingMigrations(files, existing.rows);
    for (const migration of pending) {
      await client.query(migration.sql);
      await client.query('INSERT INTO schema_migration (version, name, checksum) VALUES ($1, $2, $3)',
        [migration.version, migration.name, migration.checksum]);
    }
    await client.query('COMMIT');
    return pending.length;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  }
}
