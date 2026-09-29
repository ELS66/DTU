import { createApp } from './app.js';
import { PostgresAuthStore } from './auth/postgres-store.js';
import pg from 'pg';

const pool = process.env.DATABASE_URL ? new pg.Pool({ connectionString: process.env.DATABASE_URL }) : null;
const app = createApp(pool ? { authStore: new PostgresAuthStore(pool) } : {});
if (pool) app.addHook('onClose', async () => { await pool.end(); });
const host = process.env.HOST ?? '127.0.0.1';
const port = Number(process.env.PORT ?? '7926');

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535');
}

try {
  await app.listen({ host, port });
} catch (error) {
  app.log.error(error);
  process.exitCode = 1;
}
