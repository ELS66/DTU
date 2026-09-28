import { createHash } from 'node:crypto';

export type SerialPort = 'RS485' | 'RS232' | 'TTL';
export type Parity = 'NONE' | 'EVEN' | 'ODD';
export type ConfigRawType = 'UINT16' | 'INT16' | 'UINT32' | 'INT32' | 'FLOAT32' | 'BOOL';
export type ByteOrder = 'AB' | 'ABCD' | 'BADC' | 'CDAB' | 'DCBA';

export interface SerialConfig {
  port: SerialPort;
  baudRate: number;
  dataBits: 8;
  stopBits: 1 | 2;
  parity: Parity;
}

export interface ReadMapping {
  function: 1 | 2 | 3 | 4;
  address: number;
  count: number;
  intervalMs: number;
}

export interface WriteMapping {
  function: 5 | 6 | 16;
  address: number;
}

export interface ConfigPoint {
  pointCode: number;
  slaveId: number;
  read: ReadMapping | null;
  write: WriteMapping | null;
  rawType: ConfigRawType;
  byteOrder: ByteOrder;
}

export interface ExecutionConfig {
  serial: SerialConfig;
  points: ConfigPoint[];
}

export interface ConfigSet extends ExecutionConfig {
  protocolVersion: 1;
  releaseId: string;
  revision: number;
  expiresAt: number;
  contentHash: string;
}

const MAX_CONFIG_BYTES = 32768;
const MAX_REVISION = 0xffffffff;
const RAW_TYPES = ['UINT16', 'INT16', 'UINT32', 'INT32', 'FLOAT32', 'BOOL'] as const;
const PORTS = ['RS485', 'RS232', 'TTL'] as const;
const PARITIES = ['NONE', 'EVEN', 'ODD'] as const;
const BYTE_ORDERS = ['AB', 'ABCD', 'BADC', 'CDAB', 'DCBA'] as const;

function fail(message: string): never {
  throw new Error(`invalid config v1: ${message}`);
}

function object(value: unknown, name: string, keys: string[]): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) fail(name);
  const result = value as Record<string, unknown>;
  const actual = Object.keys(result).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    fail(`${name} fields`);
  }
  return result;
}

function integer(value: unknown, name: string, min: number, max: number): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < min || value > max) {
    fail(name);
  }
  return value;
}

function choice<T extends string>(value: unknown, name: string, allowed: readonly T[]): T {
  if (typeof value !== 'string' || !allowed.includes(value as T)) fail(name);
  return value as T;
}

function serialConfig(value: unknown): SerialConfig {
  const data = object(value, 'serial', ['port', 'baudRate', 'dataBits', 'stopBits', 'parity']);
  const dataBits = integer(data.dataBits, 'data bits', 8, 8) as 8;
  const stopBits = integer(data.stopBits, 'stop bits', 1, 2) as 1 | 2;
  return {
    port: choice(data.port, 'port', PORTS),
    baudRate: integer(data.baudRate, 'baud rate', 1200, 115200),
    dataBits,
    stopBits,
    parity: choice(data.parity, 'parity', PARITIES),
  };
}

function configPoint(value: unknown): ConfigPoint {
  const data = object(value, 'point', ['pointCode', 'slaveId', 'read', 'write', 'rawType', 'byteOrder']);
  const pointCode = integer(data.pointCode, 'point code', 1, 65535);
  const slaveId = integer(data.slaveId, 'slave ID', 1, 247);
  const rawType = choice(data.rawType, 'raw type', RAW_TYPES);
  const byteOrder = choice(data.byteOrder, 'byte order', BYTE_ORDERS);
  const isBoolean = rawType === 'BOOL';
  const isWide = rawType === 'UINT32' || rawType === 'INT32' || rawType === 'FLOAT32';
  if (isWide ? byteOrder === 'AB' : byteOrder !== 'AB') fail('byte order and raw type');

  let read: ReadMapping | null = null;
  if (data.read !== null) {
    const mapping = object(data.read, 'read', ['function', 'address', 'count', 'intervalMs']);
    const fn = integer(mapping.function, 'read function', 1, 4);
    const count = integer(mapping.count, 'read count', 1, 2);
    const address = integer(mapping.address, 'read address', 0, 65535);
    if ((isBoolean && fn !== 1 && fn !== 2) || (!isBoolean && fn !== 3 && fn !== 4)
        || count !== (isWide ? 2 : 1) || address + count > 65536) {
      fail('read mapping and raw type');
    }
    read = {
      function: fn as ReadMapping['function'],
      address,
      count,
      intervalMs: integer(mapping.intervalMs, 'read interval', 100, 3600000),
    };
  }

  let write: WriteMapping | null = null;
  if (data.write !== null) {
    const mapping = object(data.write, 'write', ['function', 'address']);
    const fn = integer(mapping.function, 'write function', 5, 16);
    const address = integer(mapping.address, 'write address', 0, 65535);
    if (fn !== (isBoolean ? 5 : isWide ? 16 : 6) || address + (isWide ? 2 : 1) > 65536) {
      fail('write mapping and raw type');
    }
    write = { function: fn as WriteMapping['function'], address };
  }
  if (read === null && write === null) fail('point has no mapping');
  return { pointCode, slaveId, read, write, rawType, byteOrder };
}

export function canonicalizeExecutionConfig(input: unknown): {
  config: ExecutionConfig;
  canonical: string;
  contentHash: string;
} {
  const data = object(input, 'execution config', ['serial', 'points']);
  if (!Array.isArray(data.points) || data.points.length < 1 || data.points.length > 128) {
    fail('point count');
  }
  const points = data.points.map(configPoint).sort((a, b) => a.pointCode - b.pointCode);
  if (points.some((point, index) => index > 0 && point.pointCode === points[index - 1]?.pointCode)) {
    fail('duplicate point code');
  }
  const config = { serial: serialConfig(data.serial), points };
  const canonical = JSON.stringify({ schemaVersion: 1, ...config });
  if (Buffer.byteLength(canonical, 'utf8') > MAX_CONFIG_BYTES) fail('config size');
  const contentHash = createHash('sha256').update(canonical, 'utf8').digest('hex');
  return { config, canonical, contentHash };
}

export function verifyConfigSet(input: unknown): ConfigSet {
  const data = object(input, 'config set', [
    'protocolVersion', 'releaseId', 'revision', 'expiresAt', 'contentHash', 'serial', 'points',
  ]);
  if (data.protocolVersion !== 1) fail('protocol version');
  if (typeof data.releaseId !== 'string'
      || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(data.releaseId)) {
    fail('release ID');
  }
  const revision = integer(data.revision, 'revision', 1, MAX_REVISION);
  const expiresAt = integer(data.expiresAt, 'expiry', 1, Number.MAX_SAFE_INTEGER);
  if (typeof data.contentHash !== 'string' || !/^[0-9a-f]{64}$/.test(data.contentHash)) {
    fail('content hash');
  }
  const { config, contentHash } = canonicalizeExecutionConfig({ serial: data.serial, points: data.points });
  if (data.contentHash !== contentHash) fail('content hash mismatch');
  return {
    protocolVersion: 1,
    releaseId: data.releaseId,
    revision,
    expiresAt,
    contentHash,
    ...config,
  };
}
