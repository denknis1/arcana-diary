// Today's free readings are used (screen 11a, spec 4.4a §4): a day page block — the title, the lead, the help link,
// a white card with a gold rule ("What Plus gives you", the benefits, "tell me when it opens" by e-mail through
// POST /api/plus/waitlist, "Not now"), then the free Card of the Day. No price on the closed stage (owner,
// 19.11.2026); never inside the answer text. Stage 4.4b §5, §8: the third benefit (the whole diary) and the line about
// the free diary's 10 readings; in the diary (`place: 'diary'`) only the white card, without the "today's readings"
// title and the Card of the Day links.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { errorMessageKey, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import { siteApi } from '../../lib/siteApi';
import type { Lang, Tool } from '../../lib/types';
import { HelpLine } from './HelpLine';

interface Props {
  lang: Lang;
  tool: Tool | null; // null in the diary: plus_view carries no tool anyway
  place?: 'limit' | 'diary';
  focusOnShow?: boolean;
}

export function PlusCard({ lang, tool, place = 'limit', focusOnShow = false }: Props) {
  const d = t(lang);
  const heading = useRef<HTMLHeadingElement>(null);
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'invalid' | ErrorKind>('idle');
  const id = `plus-${tool ?? place}`;

  useEffect(() => {
    sendEvent(analyticsEvent('plus_view', tool, lang, { place }));
    if (focusOnShow) heading.current?.focus();
  }, []);

  const submit = async (event: Event) => {
    event.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) { // the API still validates; this keeps the browser's own bubble away
      setStatus('invalid');
      return;
    }
    setStatus('sending');
    const result = await siteApi().joinWaitlist(email.trim(), lang);
    if (result.ok) setStatus('done');
    else setStatus(result.status === 422 ? 'invalid' : result.error);
  };

  const error = status === 'invalid' ? d.plusEmailError
    : status !== 'idle' && status !== 'sending' && status !== 'done' ? d[errorMessageKey(status)] : null;
  const daily = pagePath('daily', lang);

  const card = (
    <section class="plus__card" aria-labelledby={`${id}-title`}>
      <h3 id={`${id}-title`}>{d.plusGives}</h3>
      <ul>
        <li>{d.plusBenefit1}</li>
        <li>{d.plusBenefit2}</li>
        <li>{d.plusBenefit3}</li>
      </ul>
      <p class="small">{d.plusDiaryNote}</p>
      {status === 'done' ? (
        <p role="status">{d.plusDone}</p>
      ) : (
        <form class="field" onSubmit={submit} noValidate>
          <label for={`${id}-email`}>{d.plusEmailLabel}</label>
          <input
            id={`${id}-email`}
            class="input input--day"
            type="email"
            autocomplete="email"
            required
            aria-invalid={error ? 'true' : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            maxLength={254}
            placeholder={d.plusEmailPlaceholder}
            value={email}
            onInput={(e) => setEmail((e.target as HTMLInputElement).value)}
          />
          <div class="plus__row">
            <button type="submit" class="btn btn--ink" disabled={status === 'sending'}>{d.plusNotify}</button>
            {place === 'limit' ? <a href={daily}>{d.plusNotNow}</a> : null}
          </div>
          {error ? <p role="alert" id={`${id}-error`}>{error}</p> : null}
        </form>
      )}
    </section>
  );

  if (place === 'diary') return card;
  return (
    <div class="plus">
      <h2 class="display" tabIndex={-1} ref={heading}>{d.plusTitle}</h2>
      <p class="lead">{d.plusLead}</p>
      <HelpLine lang={lang} />
      {card}
      <a class="plus__daily" href={daily}>{d.plusDaily}</a>
    </div>
  );
}
