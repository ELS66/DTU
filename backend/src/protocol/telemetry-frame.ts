export type RawType = 1 | 2 | 3 | 4 | 5 | 6;
export type Quality = 0 | 1 | 2 | 3;

export interface Reading {
  pointCode: number;
  rawType: RawType;
  quality: Quality;
  sampleOffsetMs: number;
  value: number | boolean | null;
}

export interface TelemetryFrame {
  configRevision: number;
  bootId: string;
  sequence: bigint;
  sampleTimeMs: bigint;
  replayed: boolean;
  timeTrusted: boolean;
  points: Reading[];
}

const HEADER_SIZE = 47;
const POINT_HEADER_SIZE = 10;
const MAX_FRAME_SIZE = 4096;
const MAX_SEQUENCE = (1n << 63n) - 1n;
const WIDTH: Record<RawType, number> = { 1: 2, 2: 2, 3: 4, 4: 4, 5: 4, 6: 1 };

function fail(message: string): never {
  throw new Error(`invalid telemetry frame: ${message}`);
}

function isRawType(value: number): value is RawType {
  return value >= 1 && value <= 6;
}

function isQuality(value: number): value is Quality {
  return value >= 0 && value <= 3;
}

export function decodeTelemetry(frame: Buffer): TelemetryFrame {
  if (frame.length < HEADER_SIZE || frame.length > MAX_FRAME_SIZE) fail('frame length');
  if (frame.toString('ascii', 0, 2) !== 'DT' || frame[2] !== 1 || frame[3] !== 1) {
    fail('header');
  }
  const payloadLength = frame.readUInt32BE(4);
  if (HEADER_SIZE + payloadLength !== frame.length) fail('payload length');

  const configRevision = frame.readUInt32BE(8);
  const bootId = frame.toString('hex', 12, 28);
  const sequence = frame.readBigUInt64BE(28);
  const sampleTimeMs = frame.readBigInt64BE(36);
  const flags = frame.readUInt8(44);
  const pointCount = frame.readUInt16BE(45);
  const replayed = (flags & 1) !== 0;
  const timeTrusted = (flags & 2) !== 0;
  if (configRevision === 0 || sequence === 0n || sequence > MAX_SEQUENCE
      || sampleTimeMs < 0n || flags > 3 || pointCount < 1 || pointCount > 128
      || timeTrusted !== (sampleTimeMs > 0n)) {
    fail('metadata');
  }

  let cursor = HEADER_SIZE;
  const seen = new Set<number>();
  const points: Reading[] = [];
  for (let index = 0; index < pointCount; index += 1) {
    if (frame.length - cursor < POINT_HEADER_SIZE) fail('truncated point header');
    const pointCode = frame.readUInt16BE(cursor);
    const rawTypeCode = frame.readUInt8(cursor + 2);
    const qualityCode = frame.readUInt8(cursor + 3);
    const sampleOffsetMs = frame.readInt32BE(cursor + 4);
    const valueLength = frame.readUInt16BE(cursor + 8);
    cursor += POINT_HEADER_SIZE;
    if (!isRawType(rawTypeCode) || !isQuality(qualityCode)) fail('type or quality');
    const rawType = rawTypeCode;
    const quality = qualityCode;
    if (pointCode === 0 || seen.has(pointCode) ||
        valueLength !== (quality === 0 ? WIDTH[rawType] : 0) ||
        frame.length - cursor < valueLength ||
        (!timeTrusted && sampleOffsetMs !== 0) ||
        (timeTrusted && sampleTimeMs + BigInt(sampleOffsetMs) < 0n)) {
      fail('point metadata');
    }
    seen.add(pointCode);

    let value: number | boolean | null = null;
    if (quality === 0) {
      switch (rawType) {
        case 1: value = frame.readUInt16BE(cursor); break;
        case 2: value = frame.readInt16BE(cursor); break;
        case 3: value = frame.readUInt32BE(cursor); break;
        case 4: value = frame.readInt32BE(cursor); break;
        case 5:
          value = frame.readFloatBE(cursor);
          if (!Number.isFinite(value)) fail('non-finite float');
          break;
        case 6:
          if (frame[cursor] !== 0 && frame[cursor] !== 1) fail('boolean');
          value = frame[cursor] === 1;
          break;
      }
    }
    cursor += valueLength;
    points.push({ pointCode, rawType, quality, sampleOffsetMs, value });
  }
  if (cursor !== frame.length) fail('trailing data');
  return { configRevision, bootId, sequence, sampleTimeMs, replayed, timeTrusted, points };
}
