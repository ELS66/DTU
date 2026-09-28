import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import {
  decodeControlJson, parseCommandReply, parseCommandSet, parseConfigReply, parseTelemetryAck,
} from '../protocol/control-messages.js';

const vector = JSON.parse(readFileSync(
  new URL('../../../contracts/control-v1-vector.json', import.meta.url), 'utf8',
)) as Record<string, Record<string, unknown>>;

function sample(name: string): Record<string, unknown> {
  const value = vector[name];
  assert.ok(value, `missing vector ${name}`);
  return structuredClone(value);
}

test('command and reply vectors validate across the wire', () => {
  const command = sample('commandSet');
  assert.deepEqual(parseCommandSet(decodeControlJson(Buffer.from(JSON.stringify(command)))), command);
  assert.deepEqual(parseCommandReply(sample('commandReplyVerified')), sample('commandReplyVerified'));
  assert.deepEqual(parseCommandReply(sample('commandReplyFailed')), sample('commandReplyFailed'));
  assert.deepEqual(parseConfigReply(sample('configReplyApplied')), sample('configReplyApplied'));
  assert.deepEqual(parseTelemetryAck(sample('telemetryAckStored')), sample('telemetryAckStored'));
});

test('command raw values must fit the declared wire type', () => {
  const invalid = sample('commandSet');
  invalid.rawValue = true;
  assert.throws(() => parseCommandSet(invalid), /integer raw value/);
  invalid.rawType = 'BOOL';
  assert.equal(parseCommandSet(invalid).rawValue, true);
  invalid.rawType = 'FLOAT32';
  invalid.rawValue = 1e40;
  assert.throws(() => parseCommandSet(invalid), /float32 raw value/);
});

test('reply statuses and durable ACK identity reject ambiguous payloads', () => {
  const reply = sample('commandReplyVerified');
  reply.observedAt = null;
  assert.throws(() => parseCommandReply(reply), /observed value/);
  const applied = sample('configReplyApplied');
  applied.appliedRevision = 11;
  assert.throws(() => parseConfigReply(applied), /applied revision/);
  const ack = sample('telemetryAckStored');
  ack.sequence = 7;
  assert.throws(() => parseTelemetryAck(ack), /sequence/);
  ack.sequence = '9223372036854775808';
  assert.throws(() => parseTelemetryAck(ack), /sequence/);
});

test('control JSON rejects duplicate fields, invalid UTF-8 and oversized messages', () => {
  assert.throws(() => decodeControlJson(Buffer.from('{"status":"STORED","status":"REJECTED"}')), /duplicate/);
  assert.throws(() => decodeControlJson(Buffer.from([0xff, 0xfe])), /UTF-8/);
  assert.throws(() => decodeControlJson(Buffer.alloc(1025, 65)), /payload length/);
});
