// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { REVOKE_AFTER_MS, saveFile } from './download';

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('saveFile (the export of spec 4.3 §8, the calendar file of spec 4.4b §7)', () => {
  it('clicks a download link with the name, removes it, and frees the address only after a minute (review I8)', () => {
    vi.useFakeTimers({ toFake: ['setTimeout'] });
    const create = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:https://arcana.test/1');
    const revoke = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const clicked: Array<[string, string]> = [];
    const onClick = (event: MouseEvent) => {
      const link = event.target as HTMLAnchorElement;
      clicked.push([link.getAttribute('href') ?? '', link.download]);
      event.preventDefault(); // no navigation in the test
    };
    document.addEventListener('click', onClick);
    const blob = new Blob(['x'], { type: 'text/calendar;charset=utf-8' });
    saveFile(blob, 'arcana-diary-card-of-the-day.ics');
    document.removeEventListener('click', onClick);
    expect(create).toHaveBeenCalledWith(blob);
    expect(clicked).toEqual([['blob:https://arcana.test/1', 'arcana-diary-card-of-the-day.ics']]);
    expect(document.querySelector('a[download]')).toBeNull();
    vi.advanceTimersByTime(REVOKE_AFTER_MS - 1);
    expect(revoke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(revoke).toHaveBeenCalledWith('blob:https://arcana.test/1');
  });
});
