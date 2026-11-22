// The number of one request (spec 4.5 §5): a UUID v4 for every press of Draw and every follow-up sent. The flow
// sends the same number again when a request got no answer at all, so the API gives back what it already made.

type RandomSource = { getRandomValues<T extends ArrayBufferView>(array: T): T; randomUUID?: () => string };

export function newRequestId(source: RandomSource = globalThis.crypto): string {
  if (typeof source.randomUUID === 'function') return source.randomUUID();
  // older browsers without crypto.randomUUID: the same v4 layout from 16 random bytes
  const b = source.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
