// Card of the Day (screens 7a, 7b; spec 4.4a §5): tap the back → GET /api/daily → the card and its text. On 503
// the card comes from the card base (src/lib/daily.ts). "Remind me tomorrow" and "Save to diary" are stage 4.4b.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { browserFetch, createApi } from '../lib/api';
import { baseUrl, dailyNext, formatDay, localIsoDay, shownFromBase, type BaseMeaning, type DailyShown } from '../lib/daily';
import { CARD_BACK } from '../lib/deck';
import { errorMessageKey, needsHelpLink, type ErrorKind } from '../lib/errors';
import { cardPath } from '../lib/routes';
import type { Lang } from '../lib/types';
import { CardFace } from '../components/ui/CardFace';
import { HelpLine } from '../components/ui/HelpLine';

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

export default function DailyIsland({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'back' });
  const heading = useRef<HTMLHeadingElement>(null);
  const tappedAt = useRef(0);

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
    const next = dailyNext(await createApi(browserFetch()).getDaily(lang, tz), lang);
    if (next.type === 'shown') return setView({ type: 'shown', shown: next.shown });
    if (next.type === 'error') return setView({ type: 'error', error: next.error });
    const shown = await fromBase(lang, tz);
    setView(shown ? { type: 'shown', shown } : { type: 'error', error: 'unavailable' });
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
        <a href={cardPath(shown.card, lang)} onClick={() => sendEvent(analyticsEvent('more_about_cards', 'daily', lang))}>
          {fill(d.fullMeaning, { name: shown.name })}
        </a>
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
