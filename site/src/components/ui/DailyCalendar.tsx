// The Card of the Day calendar (stage 8.1 §2.2, §2.4) in the diary's "Card of the Day" tab. Signed in: the month as a
// grid, a small card on each day that had one (reversed cards turned), the streaks and the month's most frequent card
// above it; the free calendar moves between this month and the previous one. A day opens below the grid with its
// card, its text and, for a past day (today from 17:00), the evening mark. A guest gets the last 7 days of this
// device without marks; the sign-in block comes after it (DiaryIsland). Everything shown is text.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { formatDay } from '../../lib/daily';
import { cardById, cardImage } from '../../lib/deck';
import { errorMessageKey, type ErrorKind } from '../../lib/errors';
import {
  lastDays, monthGrid, monthLabel, weekdayLabels, type Calendar, type CalendarDay, type JournalApi,
  type MarkSaved,
} from '../../lib/journal';
import type { Lang } from '../../lib/types';
import { useEveningOpen } from '../../lib/useEveningOpen';
import { EveningMark } from './EveningMark';

interface Props {
  lang: Lang;
  api: JournalApi;
  guest: boolean;
  tz?: string;
  onSignedOut?: () => void;
}

// The calendar on screen stays while another month loads (dimmed, aria-busy): the buttons keep focus and the page its
// height. A failed month leaves it too, with the error and "Try again".
type Load = 'loading' | 'ready' | 'failed';

export function DailyCalendar({ lang, api, guest, tz, onSignedOut }: Props) {
  const d = t(lang);
  const [calendar, setCalendar] = useState<Calendar | null>(null);
  const [load, setLoad] = useState<Load>('loading');
  const [error, setError] = useState<ErrorKind>('other');
  const [picked, setPicked] = useState<string | null>(null);
  const counted = useRef(false);
  const wanted = useRef<string | undefined>(undefined);
  const detail = useRef<HTMLHeadingElement>(null);
  const evening = useEveningOpen();

  const fetchMonth = async (month: string | undefined) => {
    wanted.current = month;
    setLoad('loading');
    const result = await api.calendar(lang, month, tz);
    if (result.ok) {
      setCalendar(result.data);
      setLoad('ready');
      if (!counted.current) {
        counted.current = true;
        sendEvent(analyticsEvent('daily_calendar_view', null, lang, { signed_in: !guest }));
      }
      return;
    }
    if (result.status === 401 && onSignedOut) return onSignedOut();
    setError(result.error);
    setLoad('failed');
  };

  useEffect(() => { void fetchMonth(undefined); }, []);
  useEffect(() => { if (picked) detail.current?.focus(); }, [picked]); // opening a day moves the reader to it

  if (!calendar) {
    if (load === 'loading') return <section class="cal" aria-busy="true" />;
    return (
      <section class="cal">
        <p role="alert">{d[errorMessageKey(error)]}</p>
        <button type="button" class="btn btn--outline" onClick={() => void fetchMonth(wanted.current)}>{d.retry}</button>
      </section>
    );
  }

  const byDay = new Map(calendar.days.map((day) => [day.day, day]));
  const saved = (day: string, mark: MarkSaved) => setCalendar({ ...calendar,
    days: calendar.days.map((item) => (item.day === day ? { ...item, felt: mark.felt, note: mark.note } : item)) });
  const go = (month: string) => {
    if (load === 'loading' || month === calendar.month) return;
    setPicked(null);
    void fetchMonth(month);
  };

  const cell = (iso: string | null) => {
    if (iso === null) return <span class="cal__pad" />;
    const item = byDay.get(iso);
    const number = String(Number(iso.slice(8)));
    if (!item) return <span class="cal__empty">{number}</span>;
    const card = cardById(item.card.card_id);
    return (
      <button type="button" class="cal__day" aria-pressed={picked === iso} onClick={() => setPicked(iso)}
        aria-label={fill(d.calendarDayCard, { date: formatDay(iso, lang) })}>
        {card ? <img src={cardImage(card, 160)} alt="" width={160} height={274}
          class={item.card.reversed ? 'is-reversed' : undefined} /> : null}
        <span>{number}</span>
      </button>
    );
  };

  const pickedDay: CalendarDay | undefined = picked ? byDay.get(picked) : undefined;
  const canMark = (iso: string) => !guest && (iso < calendar.today || (iso === calendar.today && evening));
  const [oldest, newest] = [calendar.months[0], calendar.months[calendar.months.length - 1]];

  return (
    <section class={load === 'loading' ? 'cal cal--loading' : 'cal'} aria-labelledby="cal-title" aria-busy={load === 'loading'}>
      <p class="cal__stats">
        {fill(d.calendarStreak, { n: calendar.streak })} · {fill(d.calendarBest, { n: calendar.best_streak })}
        {calendar.top_card ? ` · ${fill(d.calendarTop, { name: calendar.top_card.name, count: calendar.top_card.count })}` : ''}
      </p>
      {guest ? (
        <>
          <h2 id="cal-title" class="h2">{d.calendarGuestTitle}</h2>
          <div class="cal__week" role="group" aria-labelledby="cal-title">
            {lastDays(calendar.today).map((iso) => <div key={iso}>{cell(iso)}</div>)}
          </div>
          {calendar.days.length === 0 ? <p class="small">{d.calendarGuestEmpty}</p> : null}
        </>
      ) : (
        <>
          <div class="cal__nav">
            <button type="button" class="btn btn--text" aria-disabled={calendar.month === oldest}
              onClick={() => go(oldest)}>{d.calendarPrev}</button>
            <h2 id="cal-title" class="h2" aria-live="polite">{calendar.month ? monthLabel(calendar.month, lang) : ''}</h2>
            <button type="button" class="btn btn--text" aria-disabled={calendar.month === newest}
              onClick={() => go(newest)}>{d.calendarNext}</button>
          </div>
          {calendar.locked ? <p>{d.calendarLocked}</p> : (
            <table class="cal__grid" aria-labelledby="cal-title">
              <thead><tr>{weekdayLabels(lang).map((name) => <th key={name} scope="col">{name}</th>)}</tr></thead>
              <tbody>
                {monthGrid(calendar.month!).map((week, i) => (
                  <tr key={i}>{week.map((iso, j) => <td key={iso ?? `pad-${i}-${j}`}>{cell(iso)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          )}
          {!calendar.locked && calendar.days.length === 0 ? <p class="small">{d.calendarEmpty}</p> : null}
        </>
      )}
      {load === 'failed' ? (
        <div>
          <p role="alert">{d[errorMessageKey(error)]}</p>
          <button type="button" class="btn btn--outline" onClick={() => void fetchMonth(wanted.current)}>{d.retry}</button>
        </div>
      ) : null}
      {pickedDay ? (
        <article class="cal__detail" aria-labelledby="cal-detail-title">
          <p class="eyebrow">{formatDay(pickedDay.day, lang)}</p>
          <h3 id="cal-detail-title" tabIndex={-1} ref={detail}>{pickedDay.card.name}{pickedDay.card.reversed ? ` · ${d.reversedTag}` : ''}</h3>
          <p class="cal__text">{pickedDay.text}</p>
          {canMark(pickedDay.day) ? (
            <EveningMark key={pickedDay.day} lang={lang} idBase={`cal-${pickedDay.day}`} place="calendar" surface="day"
              initial={{ felt: pickedDay.felt ?? null, note: pickedDay.note ?? null }}
              save={(patch) => api.mark(pickedDay.day, patch)} onSaved={(mark) => saved(pickedDay.day, mark)}
              onSignedOut={onSignedOut} />
          ) : null}
        </article>
      ) : null}
    </section>
  );
}
