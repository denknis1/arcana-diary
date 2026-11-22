import { describe, expect, it } from 'vitest';
import {
  STARTED_KEY, STARTED_MAX_AGE_MS, clearSignInStarted, clearSignedIn, isSignedIn, markSignInStarted, markSignedIn,
  signInStarted, type StorageLike,
} from './authState';
import { memoryStorage } from './testing/auth';

describe('the signed-in flag', () => {
  it('is set, read and cleared', () => {
    const storage = memoryStorage();
    expect(isSignedIn(storage)).toBe(false);
    markSignedIn(storage);
    expect(isSignedIn(storage)).toBe(true);
    clearSignedIn(storage);
    expect(isSignedIn(storage)).toBe(false);
  });

  it('is simply off when there is no storage or it throws', () => {
    const broken: StorageLike = {
      getItem: () => { throw new Error('blocked'); }, setItem: () => { throw new Error('blocked'); }, removeItem: () => {},
    };
    expect(isSignedIn(null)).toBe(false);
    expect(isSignedIn(broken)).toBe(false);
    expect(() => markSignedIn(broken)).not.toThrow();
    expect(signInStarted(0, broken)).toBeNull();
  });
});

describe('the started sign-in mark', () => {
  it('keeps the method for a day', () => {
    const storage = memoryStorage();
    markSignInStarted('google', 1000, storage);
    expect(signInStarted(1000 + STARTED_MAX_AGE_MS, storage)).toBe('google');
    expect(signInStarted(1001 + STARTED_MAX_AGE_MS, storage)).toBeNull();
    clearSignInStarted(storage);
    expect(signInStarted(1000, storage)).toBeNull();
  });

  it('ignores anything it did not write', () => {
    const storage = memoryStorage();
    for (const raw of ['nonsense', '{"method":"apple","at":1}', '{"method":"email"}']) {
      storage.setItem(STARTED_KEY, raw);
      expect(signInStarted(1, storage)).toBeNull();
    }
  });
});
