import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createApp } from '../app.js';

test('health endpoint responds without starting a network listener', async () => {
  const app = createApp();
  try {
    const response = await app.inject({ method: 'GET', url: '/health' });
    assert.equal(response.statusCode, 200);
    assert.deepEqual(response.json(), { status: 'ok' });
  } finally {
    await app.close();
  }
});
