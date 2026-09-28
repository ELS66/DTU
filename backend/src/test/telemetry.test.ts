import assert from 'node:assert/strict';
import { test } from 'node:test';
import { decodeTelemetry } from '../protocol/telemetry-frame.js';

const GOLDEN = Buffer.from(
  '44540101000000170000000c000102030405060708090a0b0c0d0e0f' +
  '00000000000000070000019e70448800020002' +
  '000102000000000000020109' +
  '0002060000000032000101', 'hex',
);

test('decodes the shared Python telemetry vector', () => {
  assert.deepEqual(decodeTelemetry(GOLDEN), {
    configRevision: 12,
    bootId: '000102030405060708090a0b0c0d0e0f',
    sequence: 7n,
    sampleTimeMs: 1780000000000n,
    replayed: false,
    timeTrusted: true,
    points: [
      { pointCode: 1, rawType: 2, quality: 0, sampleOffsetMs: 0, value: 265 },
      { pointCode: 2, rawType: 6, quality: 0, sampleOffsetMs: 50, value: true },
    ],
  });
});

test('rejects damaged frames and duplicate points', () => {
  assert.throws(() => decodeTelemetry(GOLDEN.subarray(0, -1)));
  const invalidBoolean = Buffer.from(GOLDEN);
  invalidBoolean[invalidBoolean.length - 1] = 2;
  assert.throws(() => decodeTelemetry(invalidBoolean));
  const duplicatePoint = Buffer.from(GOLDEN);
  duplicatePoint.writeUInt16BE(1, 59);
  assert.throws(() => decodeTelemetry(duplicatePoint));
});
