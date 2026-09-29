import { fileURLToPath } from 'node:url';
import pg from 'pg';
import { loadMigrations, runMigrations } from './db/migrations.js';

const url = process.env.DATABASE_URL;
if (!url) throw new Error('DATABASE_URL is required');
const directory = fileURLToPath(new URL('../migrations/', import.meta.url));
const migrations = loadMigrations(directory);
const pool = new pg.Pool({ connectionString: url });
try {
  const client = await pool.connect();
  try {
    const count = await runMigrations(client, migrations);
    console.log(`Applied ${count} migration(s); database is at V${migrations.length}.`);
  } finally {
    client.release();
  }
} finally {
  await pool.end();
}
