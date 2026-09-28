import { createApp } from './app.js';

const app = createApp();
const host = process.env.HOST ?? '127.0.0.1';
const port = Number(process.env.PORT ?? '3000');

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535');
}

try {
  await app.listen({ host, port });
} catch (error) {
  app.log.error(error);
  process.exitCode = 1;
}
