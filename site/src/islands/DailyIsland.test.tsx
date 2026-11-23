// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../lib/analytics';
import { ICS_FILENAME, ICS_TYPE } from '../lib/ics';
import { byText, cleanup, click, mount } from '../lib/testing/dom';
import { jsonResponse, routeFetch } from '../lib/testing/fakes';
import DailyIsland from './DailyIsland';

vi.mock('../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../lib/analytics')>()), sendEvent: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('the Card of the Day reminder (screen 7b; spec 4.4b §7)', () => {
  it('saves a calendar file for tomorrow 9:00 with the link, and counts remind_click', async () => {
    const served = routeFetch({ 'GET /api/daily': () => jsonResponse(200, {
      day: '2026-11-22', card: { card_id: 'major-18-moon', name: 'The Moon', reversed: false }, text: 'Rest tonight.', source: 'cache',
    }) });
    vi.stubGlobal('fetch', served.fetch);
    const saved: Array<[Blob, string]> = [];
    const { root } = await mount(<DailyIsland lang="en" save={(blob, name) => { saved.push([blob, name]); }} />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    await click(byText(root, 'Remind me tomorrow', 'button'));
    expect(saved.map(([blob, name]) => [blob.type, name])).toEqual([[ICS_TYPE, ICS_FILENAME]]);
    const text = await saved[0][0].text();
    expect(text).toContain('SUMMARY:Card of the Day — Arcana Diary\r\n');
    expect(text).toContain('BEGIN:VALARM\r\n');
    expect(text).toContain('URL:https://arcana.test/daily\r\n');
    expect(text).toContain('DURATION:PT15M\r\n');
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'remind_click', tool: 'daily', lang: 'en', params: {} });
    expect(byText(root, 'Open the file to add it to your calendar.')).toBeTruthy();
    expect(served.calls.map((c) => c.url.split('?')[0])).toEqual(['/api/daily']); // no server for the reminder
  });
});
