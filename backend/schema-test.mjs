import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import Ajv from 'ajv';

const read = (name) => JSON.parse(readFileSync(new URL(`../contracts/${name}`, import.meta.url), 'utf8'));
const schema = read('control-v1.schema.json');
const vectors = read('control-v1-vector.json');
const configVector = read('config-v1-vector.json');
const ajv = new Ajv({ strict: true });
ajv.addSchema(schema, 'control-v1');
const validate = (definition) => ajv.getSchema(`control-v1#/$defs/${definition}`);

for (const [name, definition] of Object.entries({
  commandSet: 'commandSet',
  commandReplyVerified: 'commandReply',
  commandReplyFailed: 'commandReply',
  configReplyApplied: 'configReply',
  telemetryAckStored: 'telemetryAck',
})) {
  test(`schema accepts ${name}`, () => {
    const valid = validate(definition);
    assert.equal(valid(vectors[name]), true, JSON.stringify(valid.errors));
  });
}

test('schema rejects invalid status combinations and raw values', () => {
  const command = validate('commandSet');
  const reply = validate('commandReply');
  const ack = validate('telemetryAck');
  assert.equal(command({ ...vectors.commandSet, rawValue: 40000 }), false);
  assert.equal(command({ ...vectors.commandSet, unexpected: true }), false);
  assert.equal(reply({ ...vectors.commandReplyVerified, observedAt: null }), false);
  assert.equal(reply({ ...vectors.commandReplyFailed, errorCode: null }), false);
  assert.equal(ack({ ...vectors.telemetryAckStored, sequence: 1 }), false);
});

test('schema checks config/set structure and mapping types', () => {
  const config = validate('configSet');
  const value = {
    protocolVersion: 1,
    releaseId: '1b37a40b-1736-475f-bf57-0861fcb07c5a',
    revision: 12,
    expiresAt: 1780000100000,
    contentHash: configVector.sha256,
    ...configVector.executionConfig,
  };
  assert.equal(config(value), true, JSON.stringify(config.errors));
  assert.equal(config({ ...value, points: [{ ...value.points[0], byteOrder: 'ABCD' }] }), false);
  assert.equal(config({ ...value, points: [{ ...value.points[0], read: null, write: null }] }), false);
  assert.equal(config({ ...value, serial: { ...value.serial, parity: 'INVALID' } }), false);
});
