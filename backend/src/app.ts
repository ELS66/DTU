import Fastify from 'fastify';
import { registerAuthRoutes } from './auth/routes.js';
import type { AuthStore } from './auth/store.js';

export function createApp(options: { authStore?: AuthStore } = {}) {
  const app = Fastify({ logger: true });
  app.get('/health', async () => ({ status: 'ok' }));
  if (options.authStore) registerAuthRoutes(app, options.authStore);
  return app;
}
