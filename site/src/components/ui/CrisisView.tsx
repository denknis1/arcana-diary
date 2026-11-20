// The crisis answer (spec 4.2 §3.2): warm words and help lines from the API, no cards, no reading. A line that
// takes texts without a keyword (988) gets an sms: link; findahelpline.com is a link under the fallback sentence.
import { fill, t } from '../../i18n';
import { canCall, canText, safeUrl, smsHref, telHref } from '../../lib/helplines';
import type { CrisisPayload, Lang } from '../../lib/types';
import { HelpLine } from './HelpLine';

export function CrisisView({ payload, lang }: { payload: CrisisPayload; lang: Lang }) {
  const d = t(lang);
  const c = payload.crisis;
  return (
    <div class="crisis">
      <p>{c.body}</p>
      <p>{c.not_saved}</p>
      <p>{c.contacts_intro}</p>
      <ul class="helplines">
        {payload.helplines.lines.map((line) => {
          const tel = canCall(line) ? telHref(line.number!) : null;
          const sms = canText(line) ? smsHref(line.number!) : null;
          const url = safeUrl(line.url);
          return (
            <li key={line.name}>
              <strong>{line.name}</strong>
              <span>{line.purpose}</span>
              {tel ? <a href={tel}>{fill(d.crisisCall, { number: line.number! })}</a> : null}
              {sms ? <a href={sms}>{fill(d.crisisText, { sms: line.number! })}</a> : null}
              {line.sms ? <span>{fill(d.crisisText, { sms: line.sms })}</span> : null}
              {url ? <a href={url} rel="noopener noreferrer" target="_blank">{fill(d.crisisWeb, { name: line.name })}</a> : null}
              {line.note ? <span>{line.note}</span> : null}
              {line.hours ? <span>{fill(d.crisisHours, { hours: line.hours })}</span> : null}
            </li>
          );
        })}
      </ul>
      <p>{c.fallback_contacts}</p>
      <HelpLine lang={lang} />
      <p>{c.emergency_line}</p>
      <p>{c.closing}</p>
    </div>
  );
}
