// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../../lib/analytics';
import { createJournalApi } from '../../lib/journal';
import { byText, cleanup, click, mount, waitFor } from '../../lib/testing/dom';
import { jsonResponse, routeFetch } from '../../lib/testing/fakes';
import { DailyCalendar } from './DailyCalendar';

vi.mock('../../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/analytics')>()), sendEvent: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.mocked(sendEvent).mockClear();
});

const MOON = { card_id: 'major-18-moon', name: 'The Moon', reversed: true };
const SUN = { card_id: 'major-19-sun', name: 'The Sun', reversed: false };
const month = (extra: Record<string, unknown> = {}) => ({
  guest: false, today: '2026-11-22', month: '2026-11', months: ['2026-10', '2026-11'], locked: false, streak: 3,
  best_streak: 5, top_card: { card_id: 'major-18-moon', name: 'The Moon', count: 2 },
  days: [
    { day: '2026-11-03', card: MOON, text: 'Rest <b>tonight</b>.', source: 'fallback', felt: 'partly', note: 'Slept early.' },
    { day: '2026-11-22', card: SUN, text: 'Go out.', source: 'cache', felt: null, note: null },
  ],
  ...extra,
});

function setup(routes: Parameters<typeof routeFetch>[0]) {
  const served = routeFetch(routes);
  return { served, api: createJournalApi(served.fetch) };
}

describe('the Card of the Day calendar (stage 8.1 §2.2)', () => {
  it('shows the month with small cards, the streaks and the most frequent card, and counts the view once', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    expect(root.querySelector('.cal__stats')!.textContent).toBe('Streak now: 3 · Best streak: 5 · Most frequent this month: The Moon ×2');
    const days = Array.from(root.querySelectorAll<HTMLButtonElement>('.cal__day'));
    expect(days.map((b) => b.getAttribute('aria-label'))).toEqual(['Card of Tuesday 3 November', 'Card of Sunday 22 November']);
    expect(days[0].querySelector('img')!.classList.contains('is-reversed')).toBe(true);
    expect(root.querySelectorAll('.cal__empty')).toHaveLength(28);
    expect(vi.mocked(sendEvent).mock.calls.map(([e]) => e)).toEqual([
      { name: 'daily_calendar_view', tool: null, lang: 'en', params: { signed_in: true } }]);
  });

  it('a past day opens with its text as text and its mark and note', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    await click(root.querySelector('.cal__day')!);
    const detail = root.querySelector('.cal__detail')!;
    expect(detail.querySelector('h3')!.textContent).toBe('The Moon · Reversed');
    expect(detail.querySelector('.cal__text')!.textContent).toBe('Rest <b>tonight</b>.');
    expect(detail.querySelector('b')).toBeNull();
    expect(byText(detail, 'Partly', 'button').getAttribute('aria-pressed')).toBe('true');
    expect(detail.querySelector<HTMLInputElement>('input')!.value).toBe('Slept early.');
  });

  it('today has no mark before 17:00', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 22, 10, 0));
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    await click(root.querySelectorAll('.cal__day')[1]);
    expect(root.querySelector('.cal__detail .evening')).toBeNull();
  });

  it('moves to the previous month and no further', async () => {
    const { api, served } = setup({
      'GET /api/daily/calendar': () => jsonResponse(200, month()),
      'GET /api/daily/calendar?lang=en&month=2026-10': () => jsonResponse(200, month({ month: '2026-10', days: [], top_card: null })),
    });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    expect(byText<HTMLButtonElement>(root, 'Next month', 'button').disabled).toBe(true);
    await click(byText(root, 'Previous month', 'button'));
    await waitFor(() => byText(root, 'October 2026'));
    expect(byText<HTMLButtonElement>(root, 'Previous month', 'button').disabled).toBe(true);
    expect(byText(root, 'No cards this month yet.')).toBeTruthy();
    expect(served.calls.map((c) => c.url)).toEqual(['/api/daily/calendar?lang=en', '/api/daily/calendar?lang=en&month=2026-10']);
    expect(vi.mocked(sendEvent)).toHaveBeenCalledTimes(1);
  });

  it('a guest sees the last 7 days without marks, in Spanish', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, { ...month(), guest: true, month: null,
      months: [], top_card: null, days: [{ day: '2026-11-22', card: SUN, text: 'Sal.', source: 'cache' }] }) });
    const { root } = await mount(<DailyCalendar lang="es" api={api} guest />);
    await waitFor(() => byText(root, 'Tus últimos 7 días'));
    expect(root.querySelectorAll('.cal__week > div')).toHaveLength(7);
    await click(root.querySelector('.cal__day')!);
    expect(root.querySelector('.cal__detail .evening')).toBeNull();
    expect(vi.mocked(sendEvent).mock.calls[0][0].params).toEqual({ signed_in: false });
  });
});
