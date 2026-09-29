import pg from 'pg';
import { bootstrapTenant } from './db/bootstrap.js';

const url = process.env.DATABASE_URL;
const password = process.env.DTU_BOOTSTRAP_PASSWORD;
delete process.env.DTU_BOOTSTRAP_PASSWORD;
const args = process.argv.slice(2);
const loginIndex = args.indexOf('--login');
const tenantIndex = args.indexOf('--tenant');
const loginName = loginIndex >= 0 ? args[loginIndex + 1] : undefined;
const tenantName = tenantIndex >= 0 ? args[tenantIndex + 1] : undefined;
if (!url || !password || !loginName || !tenantName) {
  throw new Error('DATABASE_URL, DTU_BOOTSTRAP_PASSWORD, --login and --tenant are required');
}

const pool = new pg.Pool({ connectionString: url });
try {
  const client = await pool.connect();
  try {
    const ids = await bootstrapTenant(client, loginName, tenantName, password);
    console.log(`Created initial tenant ${ids.tenantId} and admin user ${ids.userId}.`);
  } finally {
    client.release();
  }
} finally {
  await pool.end();
}
