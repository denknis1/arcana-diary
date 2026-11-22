import { describe, expect, it } from 'vitest';
import { NOTICE_KEY, markNotice, noticeHref, noticeOf, takeNotice, withoutNotice } from './notice';
import { memoryStorage } from './testing/auth';

describe('the home page notice', () => {
  it('says "account deleted" once and leaves a clean address', () => {
    expect(noticeHref('/es')).toBe('/es?account=deleted');
    expect(noticeOf('?account=deleted')).toBe('accountDeleted');
    expect(noticeOf('?account=other')).toBeNull();
    expect(withoutNotice('https://arcana.test/es?account=deleted&utm_source=x')).toBe('/es?utm_source=x');
  });

  it("shows the line only after this browser's own deletion, and only once (review M22)", () => {
    const storage = memoryStorage();
    expect(takeNotice('?account=deleted', storage)).toBeNull(); // a shared link alone
    markNotice('accountDeleted', storage);
    expect(storage.data[NOTICE_KEY]).toBe('accountDeleted');
    expect(takeNotice('', storage)).toBeNull(); // the mark goes with any visit of the home page
    markNotice('accountDeleted', storage);
    expect(takeNotice('?account=deleted', storage)).toBe('accountDeleted');
    expect(takeNotice('?account=deleted', storage)).toBeNull(); // once
  });
});
