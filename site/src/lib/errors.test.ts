import { describe, expect, it } from 'vitest';
import { classifyError, errorMessageKey, needsHelpLink, reasonOf } from './errors';

describe('classifyError', () => {
  it('maps every answer of api/README.md to a kind', () => {
    expect(classifyError(429, { reason: 'limit', remaining: 0 })).toBe('limit');
    expect(classifyError(429, { reason: 'ip_limit', remaining: 0 })).toBe('daycap');
    expect(classifyError(429, { reason: 'attempts' })).toBe('attempts');
    expect(classifyError(429, { reason: 'rate' })).toBe('busy');
    expect(classifyError(403, { reason: 'turnstile', sitekey: 'k' })).toBe('turnstile');
    expect(classifyError(403, { reason: 'owner_only' })).toBe('other');
    expect(classifyError(503, { reason: 'unavailable' })).toBe('unavailable');
    expect(classifyError(503, { reason: 'db' })).toBe('unavailable');
    expect(classifyError(503, null)).toBe('unavailable');
    expect(classifyError(502, null)).toBe('unavailable'); // Caddy while the API restarts
    expect(classifyError(504, null)).toBe('unavailable');
    expect(classifyError(401, null)).toBe('stage');
    expect(classifyError(401, { reason: 'auth' })).toBe('other');
    expect(classifyError(404, { reason: 'not_found' })).toBe('gone');
    expect(classifyError(0, null)).toBe('network');
    expect(classifyError(422, { reason: 'invalid', fields: ['question'] })).toBe('other');
    expect(classifyError(409, { reason: 'busy' })).toBe('other');
  });

  it('adds the help link to the 429, 403 turnstile and 503 messages only', () => {
    expect(['limit', 'busy', 'daycap', 'attempts', 'turnstile', 'unavailable'].every((k) => needsHelpLink(k as never))).toBe(true);
    expect(['stage', 'gone', 'network', 'other'].some((k) => needsHelpLink(k as never))).toBe(false);
  });

  it('has a message for every kind', () => {
    expect(errorMessageKey('busy')).toBe('errBusy');
    expect(errorMessageKey('unavailable')).toBe('errUnavailable');
    expect(errorMessageKey('limit')).toBe('plusTitle');
    expect(errorMessageKey('daycap')).toBe('errDayCap');
    expect(errorMessageKey('attempts')).toBe('followupNone');
  });

  it('reads the reason only when it is a string', () => {
    expect(reasonOf({ reason: 'limit' })).toBe('limit');
    expect(reasonOf({ reason: 3 })).toBeUndefined();
    expect(reasonOf('text')).toBeUndefined();
  });
});
