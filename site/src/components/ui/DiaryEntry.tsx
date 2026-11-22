// One diary entry (screen 4b; spec 4.4b §5) — /diary?r=<id>, GET /api/readings/{id}: the cards, the answer by
// sections, the follow-ups; "Came true / Partly / No" from 00:00 local time of the day «the reading's local date + 7
// days» (owner decision 13; change or clear it), before that the day to come back — both from the list's own rule
// (lib/diary.ts); a private note (1000 characters, counter, "Save note"); delete with a confirmation.
// A crisis entry shows only its date, the help line and "delete". Every text from the API is a text node. Only
// 401 "sign_in" means the session went (review I4): a 401 without JSON is the stage cookie — reload the page.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import type { AccountApi, DiaryEntry as Entry, Outcome } from '../../lib/accountApi';
import { analyticsEvent, sendEvent, type AnalyticsEvent } from '../../lib/analytics';
import { answerBlocks, answerFromView } from '../../lib/answer';
import type { ApiResult } from '../../lib/api';
import { NOTE_MAX, afterDays, formatDate, kindKey, noteLeft, outcomeOpen, outcomeOpensOn } from '../../lib/diary';
import { errorMessageKey, needsHelpLink, reasonOf, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import type { Lang } from '../../lib/types';
import { CardFace } from './CardFace';
import { OUTCOME_KEYS } from './DiaryList';
import { HelpLine } from './HelpLine';
import { VerdictIcon } from './icons';

const OUTCOMES: readonly Outcome[] = ['yes', 'partly', 'no'];

type Refusal = Extract<ApiResult<unknown>, { ok: false }>;

/** 401 {"reason": "sign_in"}: the session went on this device (spec 4.4b §3). */
function sessionGone(result: Refusal): boolean {
  return result.status === 401 && reasonOf(result.body) === 'sign_in';
}

/** A line for what went wrong: the help line only where the message needs it; the stage cookie reloads the page
 * (spec §3); `retry` asks again (for an entry that could not be read). */
function Problem({ error, lang, retry }: { error: ErrorKind; lang: Lang; retry?: () => void }) {
  const d = t(lang);
  const again = error === 'stage' ? () => location.reload() : retry;
  return (
    <div class="entry__error">
      <p role="alert">{d[errorMessageKey(error)]}</p>
      {needsHelpLink(error) ? <HelpLine lang={lang} /> : null}
      {again ? <button type="button" class="btn btn--outline" onClick={again}>{d.retry}</button> : null}
    </div>
  );
}

interface Props {
  lang: Lang;
  id: string;
  api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'>;
  onSignedOut: () => void;
  now?: () => Date;
  tz?: string;
  navigate?: (url: string) => void;
  send?: (event: AnalyticsEvent) => void;
}

export function DiaryEntry({ lang, id, api, onSignedOut, now = () => new Date(), tz, navigate = (url) => location.assign(url),
  send = sendEvent }: Props) {
  const d = t(lang);
  const [entry, setEntry] = useState<Entry | null>(null);
  const [error, setError] = useState<ErrorKind | null>(null); // the entry could not be read
  const [failed, setFailed] = useState<ErrorKind | null>(null); // a change could not be saved
  const [note, setNote] = useState('');
  const [noteState, setNoteState] = useState<'idle' | 'saving' | 'saved'>('idle');
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false); // an outcome is being saved: its buttons wait (review M21)
  const [removing, setRemoving] = useState(false); // one DELETE, not one per press
  const deleteButton = useRef<HTMLButtonElement>(null);
  const confirmButton = useRef<HTMLButtonElement>(null);
  const wasConfirming = useRef(false);
  const diary = pagePath('diary', lang);

  const load = async () => {
    setError(null);
    const result = await api.entry(id, tz);
    if (result.ok && result.data.in_diary) {
      setEntry(result.data);
      setNote(result.data.note ?? '');
    } else if (!result.ok && sessionGone(result)) onSignedOut();
    else setError(result.ok ? 'gone' : result.error); // a reading of this device that is not in the account: gone
  };

  useEffect(() => { void load(); }, [id]);

  useEffect(() => { // the pressed button disappears: focus goes to the one that took its place
    if (confirming) confirmButton.current?.focus();
    else if (wasConfirming.current) deleteButton.current?.focus();
    wasConfirming.current = confirming;
  }, [confirming]);

  if (error) {
    return (
      <div class="entry">
        <a class="entry__back" href={diary}>{d.diaryBack}</a>
        <Problem error={error} lang={lang} retry={error === 'gone' ? undefined : () => void load()} />
      </div>
    );
  }
  if (!entry) return <div class="entry" aria-busy="true" />; // no empty status line (review M18)

  const crisis = entry.answer_shown === 'crisis';
  const answer = answerFromView(entry);
  const headline = answer.sections.headline?.trim();

  const refused = (result: Refusal) => {
    if (sessionGone(result)) onSignedOut();
    else setFailed(result.error); // 'stage' for a 401 without JSON: the line and a reload button
  };

  const mark = async (outcome: Outcome | null) => {
    setBusy(true);
    const result = await api.patchEntry(id, { outcome });
    setBusy(false);
    if (!result.ok) return refused(result);
    setFailed(null);
    const first = entry.outcome === null; // an answer on an empty mark; a change (yes → no) is not counted again
    setEntry({ ...entry, outcome: result.data.outcome });
    if (outcome && first) {
      send(analyticsEvent('outcome_answered', null, lang, { after_days: afterDays(entry.created_at, now()), answer: outcome }));
    }
  };

  const saveNote = async (event: Event) => {
    event.preventDefault();
    setNoteState('saving');
    const result = await api.patchEntry(id, { note: note.trim() ? note : null });
    if (!result.ok) {
      setNoteState('idle');
      return refused(result);
    }
    setFailed(null);
    setNoteState('saved');
  };

  const remove = async () => {
    setRemoving(true);
    const result = await api.deleteEntry(id);
    if (!result.ok) {
      setRemoving(false);
      return refused(result);
    }
    navigate(diary);
  };

  return (
    <article class="entry" aria-labelledby="entry-title">
      <a class="entry__back" href={diary}>{d.diaryBack}</a>
      <p class="eyebrow">{formatDate(entry.created_at, lang)} · {d[kindKey(entry.kind, entry.topic)]}</p>
      <h2 id="entry-title" class="h2">{crisis ? formatDate(entry.created_at, lang) : entry.question ?? d.diaryNoQuestion}</h2>
      {crisis ? <HelpLine lang={lang} /> : (
        <>
          <div class="entry__cards">
            {entry.cards.map((card, i) => (
              <CardFace key={i} cardId={card.card_id} name={card.name} reversed={card.reversed} lang={lang} sizes="120px" />
            ))}
          </div>
          {headline ? <p class="entry__headline">{headline}</p> : null}
          {entry.soft_line ? <p class="answer__soft">{entry.soft_line}</p> : null}
          {entry.verdict ? (
            <p class="entry__verdict"><VerdictIcon value={entry.verdict.value} size={28} />{entry.verdict.label}</p>
          ) : null}
          {answerBlocks(answer, entry.cards).map((block, i) => {
            if (block.kind === 'headline') return null;
            const label = block.kind === 'card' ? block.card.name : block.kind === 'step' ? d.stepLabel : block.kind === 'why' ? d.whyPrefix : null;
            return (
              <div key={i}>
                {label ? <span class="answer__label">{label}</span> : null}
                <p class="answer__text">{block.text}</p>
              </div>
            );
          })}
          {entry.followups.map((f) => (
            <div key={f.n}>
              <p class="followup__q">{d.followupYouAsked}: {f.question}</p>
              {f.soft_line ? <p class="answer__soft">{f.soft_line}</p> : null}
              {f.answer ? <p class="answer__text">{f.answer}</p> : null}
            </div>
          ))}
          <section class="entry__outcome" aria-labelledby="outcome-title">
            <h3 id="outcome-title">{d.entryOutcomeQuestion}</h3>
            {outcomeOpen(entry.created_at, now()) ? (
              <div class="chips" role="group" aria-labelledby="outcome-title">
                {OUTCOMES.map((value) => (
                  <button key={value} type="button" class="chip chip--day" aria-pressed={entry.outcome === value} disabled={busy}
                    onClick={() => void mark(value)}>
                    {d[OUTCOME_KEYS[value]]}
                  </button>
                ))}
                {entry.outcome ? (
                  <button type="button" class="btn btn--text" disabled={busy} onClick={() => void mark(null)}>{d.entryOutcomeClear}</button>
                ) : null}
              </div>
            ) : (
              <p class="small">{fill(d.entryOutcomeLater, { date: formatDate(outcomeOpensOn(entry.created_at), lang) })}</p>
            )}
          </section>
          <form class="field entry__note" onSubmit={saveNote}>
            <label for="entry-note">{d.noteLabel}</label>
            <textarea id="entry-note" class="input input--day" rows={4} maxLength={NOTE_MAX} value={note}
              onInput={(e) => { setNote((e.target as HTMLTextAreaElement).value); setNoteState('idle'); }} />
            <p class="small" aria-live="polite">{fill(d.noteLeft, { n: noteLeft(note) })}</p>
            <button type="submit" class="btn btn--ink" disabled={noteState === 'saving'}>{d.noteSave}</button>
            {noteState === 'saved' ? <p class="small" role="status">{d.noteSaved}</p> : null}
          </form>
        </>
      )}
      {failed ? <Problem error={failed} lang={lang} /> : null}
      {confirming ? (
        <div class="notice notice--day" role="alert">
          <p>{d.entryDeleteConfirm}</p>
          <div class="plus__row">
            <button type="button" class="btn btn--ink" ref={confirmButton} disabled={removing} onClick={() => void remove()}>
              {d.entryDeleteYes}
            </button>
            <button type="button" class="btn btn--text" onClick={() => setConfirming(false)}>{d.cancel}</button>
          </div>
        </div>
      ) : (
        <button type="button" class="btn btn--text" ref={deleteButton} onClick={() => setConfirming(true)}>{d.entryDelete}</button>
      )}
    </article>
  );
}
