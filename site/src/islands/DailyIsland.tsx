// Card of the Day (screens 7a, 7b; spec 4.4a §5): tap the back → GET /api/daily → the card and its text. On 503
// the card comes from the card base (src/lib/daily.ts). Under the card "Remind me tomorrow" (spec 4.4b §7): a calendar
// file made here, no server. The card of the day is not a reading: it is not saved to the diary (spec 4.4b §2.10).
// The link to the card follows row L-EN-15 / L-ES-15 of the stage 2 matrix (owner decision 38); its "Save to diary"
// (L-EN-16, L-ES-16) is wave V1.1 (owner decision 42, 24.11.2026).
// Stage 8.1 (spec 2026-11-27 §2): under the text the streak line with the link to the calendar of the diary, and from
// 17:00 the evening mark — for an account (the API sends today's mark only to an account); a guest sees the question
// with inactive answers and a sign-in line (owner decision 56).
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { fill, t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { calendarHref, createJournalApi, STREAK_SHOWN_FROM } from '../lib/journal';
import { siteApi, siteFetch } from '../lib/siteApi';
import { baseUrl, dailyNext, formatDay, localIsoDay, shownFromBase, type BaseMeaning, type DailyShown } from '../lib/daily';
import { CARD_BACK } from '../lib/deck';
import { saveFile, type SaveFile } from '../lib/download';
import { errorMessageKey, needsHelpLink, type ErrorKind } from '../lib/errors';
import { ICS_FILENAME, ICS_TYPE, dailyReminderIcs } from '../lib/ics';
import { drawnCardLink, pagePath } from '../lib/routes';
import { useEveningOpen } from '../lib/useEveningOpen';
import type { Lang } from '../lib/types';
import { CardFace } from '../components/ui/CardFace';
import { EveningMark } from '../components/ui/EveningMark';
import { HelpLine } from '../components/ui/HelpLine';
import { PushOffer } from '../components/ui/PushOffer';

type View = { type: 'back' } | { type: 'loading' } | { type: 'shown'; shown: DailyShown } | { type: 'error'; error: ErrorKind };

function timeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

async function fromBase(lang: Lang, tz: string | undefined): Promise<DailyShown | null> {
  try {
    const response = await fetch(baseUrl(lang));
    if (!response.ok) return null;
    return shownFromBase(localIsoDay(new Date(), tz), lang, (await response.json()) as BaseMeaning[]);
  } catch {
    return null;
  }
}

export default function DailyIsland({ lang, save = saveFile }: { lang: Lang; save?: SaveFile }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'back' });
  const [reminded, setReminded] = useState(false);
  const [signedOut, setSignedOut] = useState(false); // a mark came back 401: the session ended, the line says so
  const evening = useEveningOpen();
  const heading = useRef<HTMLHeadingElement>(null);
  const tappedAt = useRef(0);
  const journal = useMemo(() => createJournalApi(siteFetch()), []);

  useEffect(() => sendEvent(analyticsEvent('tool_view', 'daily', lang)), []);

  useEffect(() => {
    if (view.type !== 'shown') return;
    sendEvent(analyticsEvent('cards_revealed', 'daily', lang, { cards_count: 1 }));
    sendEvent(analyticsEvent('reading_shown', 'daily', lang, { ms_from_draw: Date.now() - tappedAt.current }));
    heading.current?.focus();
  }, [view.type]);

  const turn = async () => {
    tappedAt.current = Date.now();
    sendEvent(analyticsEvent('draw_click', 'daily', lang, { has_question: false, entry: 'tool' }));
    setView({ type: 'loading' });
    const tz = timeZone();
    const next = dailyNext(await siteApi().getDaily(lang, tz), lang);
    if (next.type === 'shown') return setView({ type: 'shown', shown: next.shown });
    if (next.type === 'error') return setView({ type: 'error', error: next.error });
    const shown = await fromBase(lang, tz);
    setView(shown ? { type: 'shown', shown } : { type: 'error', error: 'unavailable' });
  };

  const remind = () => {
    sendEvent(analyticsEvent('remind_click', 'daily', lang));
    const text = dailyReminderIcs({ now: new Date(), lang, origin: location.origin });
    save(new Blob([text], { type: ICS_TYPE }), ICS_FILENAME);
    setReminded(true);
  };

  if (view.type === 'shown') {
    const { shown } = view;
    return (
      <section class="daily" aria-labelledby="daily-card">
        <p class="eyebrow">{formatDay(shown.day, lang)}</p>
        <CardFace cardId={shown.card.card_id} name={shown.name} reversed={shown.reversed} lang={lang} />
        <h2 id="daily-card" class="h2" tabIndex={-1} ref={heading}>
          {shown.name}{shown.reversed ? ` · ${d.reversedTag}` : ''}
        </h2>
        {shown.fromBase ? <p class="small">{d.dailyFallbackNote}</p> : null}
        <p class="daily__text">{shown.text}</p>
        {drawnCardLink({ card_id: shown.card.card_id, reversed: shown.reversed }, 'daily', lang).map((link) => (
          <a key={link.href} href={link.href} onClick={() => sendEvent(analyticsEvent('more_about_cards', 'daily', lang))}>
            {link.text}
          </a>
        ))}
        <p class="daily__streak">
          {shown.streak >= STREAK_SHOWN_FROM ? `${fill(d.dailyStreak, { n: shown.streak })} · ` : ''}
          <a href={calendarHref(lang)}>{d.dailyCalendarLink}</a>
        </p>
        {!shown.fromBase && evening ? (
          <EveningMark lang={lang} idBase="daily-mark" initial={shown.mark ?? { felt: null, note: null }} place="daily"
            surface="night" guest={shown.mark === null || signedOut} save={(patch) => journal.mark(shown.day, patch)}
            onSignedOut={() => setSignedOut(true)} signInHref={pagePath('diary', lang)} />
        ) : null}
        <button type="button" class="btn btn--outline" onClick={remind}>{d.remindTomorrow}</button>
        <p class="small" role="status">{reminded ? d.remindDone : ''}</p>
        {shown.fromBase ? null : <PushOffer lang={lang} streak={shown.streak} />}
      </section>
    );
  }

  return (
    <section class="daily" aria-label={d.dailyEyebrow}>
      <button type="button" class="daily__back" onClick={() => (view.type === 'loading' ? undefined : turn())} aria-disabled={view.type === 'loading'}>
        <img src={CARD_BACK} alt="" />
        <span>{view.type === 'loading' ? d.dailyLoading : d.dailyTap}</span>
      </button>
      <p class="small" role="status" aria-live="polite">{view.type === 'loading' ? d.dailyLoading : ''}</p>
      {view.type === 'error' ? (
        <>
          <p role="alert">{view.error === 'unavailable' ? d.dailyError : d[errorMessageKey(view.error)]}</p>
          {needsHelpLink(view.error) ? <HelpLine lang={lang} /> : null}
        </>
      ) : null}
      <p class="small">{d.dailyNote}</p>
    </section>
  );
}
