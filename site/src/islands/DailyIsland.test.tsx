// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { t } from '../i18n';
import { sendEvent } from '../lib/analytics';
import { ICS_FILENAME, ICS_TYPE } from '../lib/ics';
import { byText, cleanup, click, mount, submit, typeInto } from '../lib/testing/dom';
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

// Owner decision 38: the link under the Card of the Day follows rows L-EN-15 / L-ES-15 of the stage 2 matrix
// (tools/site/check_links.py names this file for them). "Save to diary" (L-EN-16, L-ES-16) is wave V1.1: the Card
// of the Day is not a reading and is not saved (spec 4.4b §2.10, owner decision 42).
describe('the link under the Card of the Day (stage 2 matrix, owner decision 38)', () => {
  it.each([
    ['L-EN-15', 'en', 'The Moon', '/cards/the-moon', "Today's card: The Moon"],
    ['L-ES-15', 'es', 'La Luna', '/es/cartas/la-luna', 'Carta de hoy: La Luna'],
  ] as const)('%s: %s — the card page with "%s" filled in', async (_row, lang, name, href, text) => {
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': () => jsonResponse(200, {
      day: '2026-11-22', card: { card_id: 'major-18-moon', name, reversed: true }, text: 'Rest tonight.', source: 'cache',
    }) }).fetch);
    const { root } = await mount(<DailyIsland lang={lang} />);
    await click(byText(root, t(lang).dailyTap, 'span').closest('button')!);
    const link = byText<HTMLAnchorElement>(root, text, 'a');
    expect(link.getAttribute('href')).toBe(href);
    const links = Array.from(root.querySelectorAll<HTMLAnchorElement>('.daily a')).map((a) => a.getAttribute('href'));
    expect(links.filter((h) => h === href)).toHaveLength(1); // stage 8.1: the calendar link is the only other one
    expect(links).toHaveLength(2);
  });
});

// Stage 8.1 (spec 2026-11-27 §2.1, §2.3): the streak line, the calendar link and the evening mark.
describe('the Card of the Day as a habit (stage 8.1)', () => {
  const card = (extra: Record<string, unknown>) => () => jsonResponse(200, {
    day: '2026-11-22', card: { card_id: 'major-18-moon', name: 'The Moon', reversed: false }, text: 'Rest tonight.',
    source: 'cache', streak: 1, best_streak: 1, mark: null, ...extra,
  });

  afterEach(() => vi.useRealTimers());

  it.each([
    ['en', 'Day 4 in a row · Your month in cards', '/diary?tab=daily'],
    ['es', 'Día 4 seguido · Tu mes en cartas', '/es/diario?tab=daily'],
  ] as const)('%s: the streak line links the calendar', async (lang, line, href) => {
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({ streak: 4, best_streak: 6 }) }).fetch);
    const { root } = await mount(<DailyIsland lang={lang} />);
    await click(byText(root, t(lang).dailyTap, 'span').closest('button')!);
    const streak = root.querySelector('.daily__streak')!;
    expect(streak.textContent).toBe(line);
    expect(streak.querySelector('a')!.getAttribute('href')).toBe(href);
  });

  it('the first day shows only the calendar link', async () => {
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({}) }).fetch);
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(root.querySelector('.daily__streak')!.textContent).toBe('Your month in cards');
  });

  it('an account sees the evening question from 17:00; a mark is saved and counted once, the note never', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 18, 0));
    const served = routeFetch({
      'GET /api/daily': card({ mark: { felt: null, note: null } }),
      'PUT /api/daily/2026-11-22': (call) => jsonResponse(200, { day: '2026-11-22', felt: 'partly', note: null, noted_at: 'x',
        ...(call.body as object) }),
    });
    vi.stubGlobal('fetch', served.fetch);
    vi.mocked(sendEvent).mockClear();
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(byText(root, "Did today's card show up in your day?")).toBeTruthy();
    await click(byText(root, 'Partly', 'button'));
    expect(byText(root, 'Partly', 'button').getAttribute('aria-pressed')).toBe('true');
    await click(byText(root, 'Yes', 'button'));
    const input = root.querySelector<HTMLInputElement>('#daily-mark-note')!;
    expect(input.maxLength).toBe(280);
    await typeInto(input, 'The talk went well.');
    await submit(input.closest('form')!);
    expect(served.calls.filter((c) => c.method === 'PUT').map((c) => c.body)).toEqual([
      { felt: 'partly' }, { felt: 'yes' }, { note: 'The talk went well.' }]);
    const felt = vi.mocked(sendEvent).mock.calls.map(([e]) => e).filter((e) => e.name === 'daily_felt');
    expect(felt).toEqual([{ name: 'daily_felt', tool: null, lang: 'en', params: { place: 'daily' } }]);
    expect(JSON.stringify(vi.mocked(sendEvent).mock.calls)).not.toContain('talk went well');
  });

  it('before 17:00 there is no evening question; a guest after 17:00 sees it inactive, with the sign-in line', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 16, 59));
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({ mark: { felt: null, note: null } }) }).fetch);
    const first = await mount(<DailyIsland lang="en" />);
    await click(byText(first.root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(first.root.querySelector('.evening')).toBeNull();
    cleanup();
    vi.setSystemTime(new Date(2026, 10, 22, 21, 0));
    const served = routeFetch({ 'GET /api/daily': card({ mark: null }) });
    vi.stubGlobal('fetch', served.fetch);
    const guest = await mount(<DailyIsland lang="en" />);
    await click(byText(guest.root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(byText(guest.root, "Did today's card show up in your day?")).toBeTruthy();
    expect(byText(guest.root, 'Sign in to mark your days and keep your cards')).toBeTruthy();
    const yes = byText<HTMLButtonElement>(guest.root, 'Yes', 'button');
    expect(yes.disabled).toBe(true);
    await click(yes);
    expect(guest.root.querySelector('.evening input')).toBeNull();
    expect(served.calls.filter((c) => c.method === 'PUT')).toEqual([]);
  });

  it('a guest\'s sign-in line is a link to the diary, which has the sign-in; one link per address (review M1)', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 21, 0));
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({ mark: null, streak: 3 }) }).fetch);
    const { root } = await mount(<DailyIsland lang="es" />);
    await click(byText(root, t('es').dailyTap, 'span').closest('button')!);
    const link = byText(root, t('es').eveningSignIn, 'a');
    expect(link.getAttribute('href')).toBe('/es/diario');
    const hrefs = Array.from(root.querySelectorAll('a')).map((a) => a.getAttribute('href'));
    expect(new Set(hrefs).size).toBe(hrefs.length);
    vi.useRealTimers();
  });

  it('choosing Partly does not wipe a line typed and not saved yet (review I3)', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 18, 0));
    const served = routeFetch({
      'GET /api/daily': card({ mark: { felt: null, note: null } }),
      'PUT /api/daily/2026-11-22': (call) => jsonResponse(200, { day: '2026-11-22', felt: null, note: null, noted_at: null, ...(call.body as object) }),
    });
    vi.stubGlobal('fetch', served.fetch);
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    const input = root.querySelector<HTMLInputElement>('#daily-mark-note')!;
    await typeInto(input, 'Not saved yet');
    await click(byText(root, 'Partly', 'button'));
    expect(root.querySelector<HTMLInputElement>('#daily-mark-note')!.value).toBe('Not saved yet');
    expect(served.calls.filter((c) => c.method === 'PUT').map((c) => c.body)).toEqual([{ felt: 'partly' }]);
    vi.useRealTimers();
  });

  it('a 401 on a mark shows the sign-in line, not "couldn\'t save" (review M9)', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 18, 0));
    vi.stubGlobal('fetch', routeFetch({
      'GET /api/daily': card({ mark: { felt: null, note: null } }),
      'PUT /api/daily/2026-11-22': () => jsonResponse(401, { detail: 'no session' }),
    }).fetch);
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    await click(byText(root, 'Yes', 'button'));
    expect(byText(root, 'Sign in to mark your days and keep your cards')).toBeTruthy();
    expect(root.textContent).not.toContain("We couldn't save that");
    expect(byText<HTMLButtonElement>(root, 'Yes', 'button').disabled).toBe(true);
    vi.useRealTimers();
  });

  it('the evening question appears at 17:00 on a page left open (review M2)', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] });
    vi.setSystemTime(new Date(2026, 10, 22, 16, 40));
    vi.stubGlobal('fetch', routeFetch({ 'GET /api/daily': card({ mark: { felt: null, note: null } }) }).fetch);
    const { root } = await mount(<DailyIsland lang="en" />);
    await click(byText(root, 'Tap to turn over your card', 'span').closest('button')!);
    expect(root.querySelector('.evening')).toBeNull();
    vi.setSystemTime(new Date(2026, 10, 22, 17, 1));
    await act(() => { vi.advanceTimersByTime(60_000); });
    expect(root.querySelector('.evening')).not.toBeNull();
    vi.useRealTimers();
  });
});
