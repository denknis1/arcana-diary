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
  eveningOpen, lastDays, monthGrid, monthLabel, weekdayLabels, type Calendar, type CalendarDay, type JournalApi,
  type MarkSaved,
} from '../../lib/journal';
import type { Lang } from '../../lib/types';
import { EveningMark } from './EveningMark';

interface Props {
  lang: Lang;
  api: JournalApi;
  guest: boolean;
  tz?: string;
  onSignedOut?: () => void;
}

type State = { type: 'loading' } | { type: 'ready'; calendar: Calendar } | { type: 'failed'; error: ErrorKind };

export function DailyCalendar({ lang, api, guest, tz, onSignedOut }: Props) {
  const d = t(lang);
  const [month, setMonth] = useState<string | undefined>(undefined);
  const [state, setState] = useState<State>({ type: 'loading' });
  const [picked, setPicked] = useState<string | null>(null);
  const counted = useRef(false);

  const load = async (wanted: string | undefined) => {
    setState({ type: 'loading' });
    const result = await api.calendar(lang, wanted, tz);
    if (result.ok) {
      setState({ type: 'ready', calendar: result.data });
      if (!counted.current) {
        counted.current = true;
        sendEvent(analyticsEvent('daily_calendar_view', null, lang, { signed_in: !guest }));
      }
      return;
    }
    if (result.status === 401 && onSignedOut) return onSignedOut();
    setState({ type: 'failed', error: result.error });
  };

  useEffect(() => { void load(month); }, [month]);

  if (state.type === 'loading') return <section class="cal" aria-busy="true" />;
  if (state.type === 'failed') return <section class="cal"><p role="alert">{d[errorMessageKey(state.error)]}</p></section>;

  const { calendar } = state;
  const byDay = new Map(calendar.days.map((day) => [day.day, day]));
  const saved = (day: string, mark: MarkSaved) => setState({ type: 'ready', calendar: { ...calendar,
    days: calendar.days.map((item) => (item.day === day ? { ...item, felt: mark.felt, note: mark.note } : item)) } });

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
  const canMark = (iso: string) => !guest && (iso < calendar.today || (iso === calendar.today && eveningOpen(new Date())));
  const [oldest, newest] = [calendar.months[0], calendar.months[calendar.months.length - 1]];

  return (
    <section class="cal" aria-labelledby="cal-title">
      <p class="cal__stats">
        {fill(d.calendarStreak, { n: calendar.streak })} · {fill(d.calendarBest, { n: calendar.best_streak })}
        {calendar.top_card ? ` · ${fill(d.calendarTop, { name: calendar.top_card.name, count: calendar.top_card.count })}` : ''}
      </p>
      {guest ? (
        <>
          <h2 id="cal-title" class="h2">{d.calendarGuestTitle}</h2>
          <div class="cal__week">{lastDays(calendar.today).map((iso) => <div key={iso}>{cell(iso)}</div>)}</div>
        </>
      ) : (
        <>
          <div class="cal__nav">
            <button type="button" class="btn btn--text" disabled={calendar.month === oldest}
              onClick={() => { setPicked(null); setMonth(oldest); }}>{d.calendarPrev}</button>
            <h2 id="cal-title" class="h2">{calendar.month ? monthLabel(calendar.month, lang) : ''}</h2>
            <button type="button" class="btn btn--text" disabled={calendar.month === newest}
              onClick={() => { setPicked(null); setMonth(newest); }}>{d.calendarNext}</button>
          </div>
          {calendar.locked ? <p>{d.calendarLocked}</p> : (
            <table class="cal__grid">
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
      {pickedDay ? (
        <article class="cal__detail" aria-labelledby="cal-detail-title">
          <p class="eyebrow">{formatDay(pickedDay.day, lang)}</p>
          <h3 id="cal-detail-title">{pickedDay.card.name}{pickedDay.card.reversed ? ` · ${d.reversedTag}` : ''}</h3>
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
