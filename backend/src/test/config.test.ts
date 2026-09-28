import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { canonicalizeExecutionConfig, verifyConfigSet } from '../protocol/config-release.js';

const vector = JSON.parse(readFileSync(
  new URL('../../../contracts/config-v1-vector.json', import.meta.url), 'utf8',
)) as {
  executionConfig: { serial: unknown; points: unknown[] };
  canonicalUtf8: string;
  sha256: string;
};

test('config canonical bytes and SHA256 match the Python vector', () => {
  const result = canonicalizeExecutionConfig(vector.executionConfig);
  assert.equal(result.canonical, vector.canonicalUtf8);
  assert.equal(result.contentHash, vector.sha256);
  assert.deepEqual(result.config.points.map((point) => point.pointCode), [1, 2]);
  const reversed = {
    serial: vector.executionConfig.serial,
    points: [...vector.executionConfig.points].reverse(),
  };
  assert.equal(canonicalizeExecutionConfig(reversed).contentHash, vector.sha256);
});

test('config set verifies its content hash and rejects changed mappings', () => {
  const release = {
    protocolVersion: 1,
    releaseId: '1b37a40b-1736-475f-bf57-0861fcb07c5a',
    revision: 12,
    expiresAt: 1780000100000,
    contentHash: vector.sha256,
    ...vector.executionConfig,
  };
  assert.equal(verifyConfigSet(release).contentHash, vector.sha256);
  const modified = structuredClone(release);
  (modified.points[0] as { slaveId: number }).slaveId = 2;
  assert.throws(() => verifyConfigSet(modified), /hash mismatch/);
});

test('config rejects duplicate points, invalid byte order and extra fields', () => {
  const duplicate = structuredClone(vector.executionConfig);
  duplicate.points.push(structuredClone(duplicate.points[0]));
  assert.throws(() => canonicalizeExecutionConfig(duplicate), /duplicate point code/);
  const invalid = structuredClone(vector.executionConfig);
  (invalid.points[0] as { byteOrder: string }).byteOrder = 'DCBA';
  assert.throws(() => canonicalizeExecutionConfig(invalid), /byte order/);
  assert.throws(() => canonicalizeExecutionConfig({ ...vector.executionConfig, tenantId: 'forged' }), /fields/);
});
