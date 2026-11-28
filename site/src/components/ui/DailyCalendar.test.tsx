// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../../lib/analytics';
import { createJournalApi } from '../../lib/journal';
import { byText, cleanup, click, mount, settle, waitFor } from '../../lib/testing/dom';
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
    expect(byText(root, 'Next month', 'button').getAttribute('aria-disabled')).toBe('true');
    await click(byText(root, 'Previous month', 'button'));
    await waitFor(() => byText(root, 'October 2026'));
    expect(byText(root, 'Previous month', 'button').getAttribute('aria-disabled')).toBe('true');
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

  it('keeps the previous month, the buttons and the focus while the next month loads (review I4)', async () => {
    let release: (response: Response) => void = () => {};
    const fetchFn = async (url: string) => (url.includes('month=2026-10')
      ? new Promise<Response>((resolve) => { release = resolve; })
      : jsonResponse(200, month()));
    const { root } = await mount(<DailyCalendar lang="en" api={createJournalApi(fetchFn)} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    const previous = byText(root, 'Previous month', 'button');
    previous.focus();
    await click(previous);
    expect(root.querySelector('.cal')!.getAttribute('aria-busy')).toBe('true');
    expect(byText(root, 'November 2026')).toBeTruthy(); // still there, dimmed
    expect(root.querySelectorAll('.cal__day')).toHaveLength(2);
    expect(byText(root, 'Previous month', 'button')).toBe(previous);
    expect(document.activeElement).toBe(previous);
    await act(() => { release(jsonResponse(200, month({ month: '2026-10', days: [], top_card: null }))); });
    await settle();
    await waitFor(() => byText(root, 'October 2026'));
    expect(root.querySelector('.cal')!.getAttribute('aria-busy')).toBe('false');
    expect(document.activeElement).toBe(byText(root, 'Previous month', 'button'));
  });

  it('a failed month keeps the calendar and the buttons and offers "Try again" (review I4)', async () => {
    let answers = [503, 200];
    const fetchFn = async (url: string) => (url.includes('month=2026-10')
      ? jsonResponse(answers.shift()!, answers.length === 1 ? { detail: 'down' } : month({ month: '2026-10', days: [], top_card: null }))
      : jsonResponse(200, month()));
    const { root } = await mount(<DailyCalendar lang="en" api={createJournalApi(fetchFn)} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    await click(byText(root, 'Previous month', 'button'));
    await waitFor(() => root.querySelector('[role="alert"]'));
    expect(byText(root, 'November 2026')).toBeTruthy();
    expect(byText(root, 'Next month', 'button')).toBeTruthy();
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => byText(root, 'October 2026'));
    expect(root.querySelector('[role="alert"]')).toBeNull();
  });

  it('a failed first load shows the error with "Try again"', async () => {
    let up = false;
    const fetchFn = async () => (up ? jsonResponse(200, month()) : jsonResponse(429, { detail: 'slow down' }));
    const { root } = await mount(<DailyCalendar lang="en" api={createJournalApi(fetchFn)} guest={false} />);
    await waitFor(() => root.querySelector('[role="alert"]'));
    up = true;
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => byText(root, 'November 2026'));
  });

  it('the grid has a name, and opening a day moves the focus to it (review M3)', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    const table = root.querySelector('table')!;
    expect(root.querySelector(`#${table.getAttribute('aria-labelledby')}`)!.textContent).toBe('November 2026');
    await click(root.querySelector('.cal__day')!);
    expect(document.activeElement).toBe(root.querySelector('#cal-detail-title'));
  });

  it('a guest with no cards sees a line, not seven bare numbers (review M10)', async () => {
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, { ...month(), guest: true, month: null,
      months: [], top_card: null, days: [] }) });
    const { root } = await mount(<DailyCalendar lang="es" api={api} guest />);
    await waitFor(() => byText(root, 'Todavía no hay cartas en los últimos 7 días.'));
  });

  it('the evening mark appears at 17:00 on a page left open, by the clock and when the tab returns (review M2)', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] });
    vi.setSystemTime(new Date(2026, 10, 22, 16, 59));
    const { api } = setup({ 'GET /api/daily/calendar': () => jsonResponse(200, month()) });
    const { root } = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(root, 'November 2026'));
    await click(root.querySelectorAll('.cal__day')[1]);
    expect(root.querySelector('.cal__detail .evening')).toBeNull();
    vi.setSystemTime(new Date(2026, 10, 22, 17, 0, 30));
    await act(() => { vi.advanceTimersByTime(60_000); });
    expect(root.querySelector('.cal__detail .evening')).not.toBeNull();
    cleanup();
    vi.setSystemTime(new Date(2026, 10, 22, 16, 0));
    const again = await mount(<DailyCalendar lang="en" api={api} guest={false} />);
    await waitFor(() => byText(again.root, 'November 2026'));
    await click(again.root.querySelectorAll('.cal__day')[1]);
    expect(again.root.querySelector('.cal__detail .evening')).toBeNull();
    vi.setSystemTime(new Date(2026, 10, 22, 19, 0));
    await act(() => { document.dispatchEvent(new Event('visibilitychange')); });
    expect(again.root.querySelector('.cal__detail .evening')).not.toBeNull();
  });
});
