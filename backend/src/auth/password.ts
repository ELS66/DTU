import { randomBytes, scrypt, timingSafeEqual } from 'node:crypto';

const COST = 16384;
const BLOCK_SIZE = 8;
const PARALLELISM = 1;
const KEY_LENGTH = 32;

const derive = (password: string, salt: Buffer): Promise<Buffer> => new Promise((resolve, reject) => {
  scrypt(password, salt, KEY_LENGTH,
    { N: COST, r: BLOCK_SIZE, p: PARALLELISM, maxmem: 64 * 1024 * 1024 },
    (error, derived) => error ? reject(error) : resolve(derived));
});

export async function hashPassword(password: string): Promise<string> {
  if (password.length < 12 || password.length > 1024) {
    throw new Error('password length must be 12..1024 characters');
  }
  const salt = randomBytes(16);
  const hash = await derive(password, salt);
  return `scrypt$${COST}$${BLOCK_SIZE}$${PARALLELISM}$${salt.toString('hex')}$${hash.toString('hex')}`;
}

export async function verifyPassword(password: string, encoded: string): Promise<boolean> {
  const parts = encoded.split('$');
  if (parts.length !== 6 || parts[0] !== 'scrypt' || parts[1] !== String(COST)
      || parts[2] !== String(BLOCK_SIZE) || parts[3] !== String(PARALLELISM)
      || !/^[0-9a-f]{32}$/.test(parts[4] ?? '') || !/^[0-9a-f]{64}$/.test(parts[5] ?? '')) {
    return false;
  }
  const salt = Buffer.from(parts[4]!, 'hex');
  const expected = Buffer.from(parts[5]!, 'hex');
  const actual = await derive(password, salt);
  return timingSafeEqual(actual, expected);
}
