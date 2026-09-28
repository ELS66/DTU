import type { ConfigRawType } from './config-release.js';

export interface CommandSet {
  protocolVersion: 1;
  commandId: string;
  configRevision: number;
  expiresAt: number;
  pointCode: number;
  rawType: ConfigRawType;
  rawValue: number | boolean;
}

export type CommandReplyStatus = 'RECEIVED' | 'EXECUTING' | 'WRITE_ACKED' | 'VERIFIED' | 'FAILED' | 'REJECTED';

export interface CommandReply {
  protocolVersion: 1;
  commandId: string;
  configRevision: number;
  status: CommandReplyStatus;
  errorCode: string | null;
  observedRawValue: number | boolean | null;
  observedAt: number | null;
}

export interface ConfigReply {
  protocolVersion: 1;
  releaseId: string;
  revision: number;
  status: 'RECEIVED' | 'APPLIED' | 'REJECTED';
  errorCode: string | null;
  appliedRevision: number;
}

export interface TelemetryAck {
  protocolVersion: 1;
  bootId: string;
  sequence: string;
  status: 'STORED' | 'REJECTED';
  errorCode: string | null;
}

const MAX_MESSAGE_BYTES = 1024;
const MAX_REVISION = 0xffffffff;
const MAX_SEQUENCE = (1n << 63n) - 1n;
const MAX_FLOAT32 = 3.4028234663852886e38;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const ERROR_CODE = /^[A-Z][A-Z0-9_]{0,63}$/;
const RAW_TYPES = ['UINT16', 'INT16', 'UINT32', 'INT32', 'FLOAT32', 'BOOL'] as const;

function fail(message: string): never {
  throw new Error(`invalid control message v1: ${message}`);
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

function uuid(value: unknown, name: string): string {
  if (typeof value !== 'string' || !UUID.test(value)) fail(name);
  return value;
}

function version(value: unknown): 1 {
  if (value !== 1) fail('protocol version');
  return 1;
}

function errorCode(value: unknown, required: boolean): string | null {
  if (value === null && !required) return null;
  if (typeof value !== 'string' || !ERROR_CODE.test(value) || !required) fail('error code');
  return value;
}

function observedValue(value: unknown): number | boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  fail('observed raw value');
}

function commandValue(rawType: ConfigRawType, value: unknown): number | boolean {
  if (rawType === 'BOOL') {
    if (typeof value !== 'boolean') fail('boolean raw value');
    return value;
  }
  if (rawType === 'FLOAT32') {
    if (typeof value !== 'number' || !Number.isFinite(value) || Math.abs(value) > MAX_FLOAT32) {
      fail('float32 raw value');
    }
    return value;
  }
  const limits: Record<Exclude<ConfigRawType, 'BOOL' | 'FLOAT32'>, [number, number]> = {
    UINT16: [0, 65535],
    INT16: [-32768, 32767],
    UINT32: [0, 0xffffffff],
    INT32: [-0x80000000, 0x7fffffff],
  };
  const [min, max] = limits[rawType];
  return integer(value, 'integer raw value', min, max);
}

export function parseCommandSet(input: unknown): CommandSet {
  const data = object(input, 'command set', [
    'protocolVersion', 'commandId', 'configRevision', 'expiresAt', 'pointCode', 'rawType', 'rawValue',
  ]);
  const rawType = choice(data.rawType, 'raw type', RAW_TYPES);
  return {
    protocolVersion: version(data.protocolVersion),
    commandId: uuid(data.commandId, 'command ID'),
    configRevision: integer(data.configRevision, 'config revision', 1, MAX_REVISION),
    expiresAt: integer(data.expiresAt, 'expiry', 1, Number.MAX_SAFE_INTEGER),
    pointCode: integer(data.pointCode, 'point code', 1, 65535),
    rawType,
    rawValue: commandValue(rawType, data.rawValue),
  };
}

export function parseCommandReply(input: unknown): CommandReply {
  const data = object(input, 'command reply', [
    'protocolVersion', 'commandId', 'configRevision', 'status', 'errorCode',
    'observedRawValue', 'observedAt',
  ]);
  const status = choice(data.status, 'command status', [
    'RECEIVED', 'EXECUTING', 'WRITE_ACKED', 'VERIFIED', 'FAILED', 'REJECTED',
  ] as const);
  const verified = status === 'VERIFIED';
  if ((verified && (data.observedRawValue === null || data.observedAt === null))
      || (!verified && (data.observedRawValue !== null || data.observedAt !== null))) {
    fail('observed value and status');
  }
  return {
    protocolVersion: version(data.protocolVersion),
    commandId: uuid(data.commandId, 'command ID'),
    configRevision: integer(data.configRevision, 'config revision', 1, MAX_REVISION),
    status,
    errorCode: errorCode(data.errorCode, status === 'FAILED' || status === 'REJECTED'),
    observedRawValue: verified ? observedValue(data.observedRawValue) : null,
    observedAt: verified ? integer(data.observedAt, 'observed time', 1, Number.MAX_SAFE_INTEGER) : null,
  };
}

export function parseConfigReply(input: unknown): ConfigReply {
  const data = object(input, 'config reply', [
    'protocolVersion', 'releaseId', 'revision', 'status', 'errorCode', 'appliedRevision',
  ]);
  const revision = integer(data.revision, 'revision', 1, MAX_REVISION);
  const status = choice(data.status, 'config status', ['RECEIVED', 'APPLIED', 'REJECTED'] as const);
  const appliedRevision = integer(data.appliedRevision, 'applied revision', 0, MAX_REVISION);
  if (status === 'APPLIED' && appliedRevision !== revision) fail('applied revision mismatch');
  return {
    protocolVersion: version(data.protocolVersion),
    releaseId: uuid(data.releaseId, 'release ID'),
    revision,
    status,
    errorCode: errorCode(data.errorCode, status === 'REJECTED'),
    appliedRevision,
  };
}

export function parseTelemetryAck(input: unknown): TelemetryAck {
  const data = object(input, 'telemetry ack', [
    'protocolVersion', 'bootId', 'sequence', 'status', 'errorCode',
  ]);
  if (typeof data.bootId !== 'string' || !/^[0-9a-f]{32}$/.test(data.bootId)) fail('boot ID');
  if (typeof data.sequence !== 'string' || !/^[1-9][0-9]{0,18}$/.test(data.sequence)
      || BigInt(data.sequence) > MAX_SEQUENCE) fail('sequence');
  const status = choice(data.status, 'ack status', ['STORED', 'REJECTED'] as const);
  return {
    protocolVersion: version(data.protocolVersion),
    bootId: data.bootId,
    sequence: data.sequence,
    status,
    errorCode: errorCode(data.errorCode, status === 'REJECTED'),
  };
}

export function decodeControlJson(payload: Buffer): unknown {
  if (payload.length < 2 || payload.length > MAX_MESSAGE_BYTES) fail('payload length');
  let source: string;
  let value: unknown;
  try {
    source = new TextDecoder('utf-8', { fatal: true }).decode(payload);
    value = JSON.parse(source) as unknown;
  } catch {
    return fail('JSON or UTF-8');
  }
  rejectDuplicateTopLevelKeys(source);
  return value;
}

function rejectDuplicateTopLevelKeys(source: string): void {
  const seen = new Set<string>();
  let depth = 0;
  let inString = false;
  let escaped = false;
  let expectingKey = false;
  let stringStart = 0;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    if (inString) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === '"') {
        inString = false;
        if (depth === 1 && expectingKey) {
          const key = JSON.parse(source.slice(stringStart, index + 1)) as string;
          if (seen.has(key)) fail('duplicate JSON field');
          seen.add(key);
          expectingKey = false;
        }
      }
    } else if (char === '"') {
      inString = true;
      stringStart = index;
    } else if (char === '{') {
      depth += 1;
      if (depth === 1) expectingKey = true;
    } else if (char === '}') {
      depth -= 1;
    } else if (char === ',' && depth === 1) {
      expectingKey = true;
    }
  }
}
