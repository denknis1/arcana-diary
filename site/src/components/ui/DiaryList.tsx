// The diary list (screen 4a; spec 4.4b §5): the newest readings first — date, kind, question (or "no question"),
// small cards, the answer's headline, the "did it come true?" mark and a note mark; a crisis entry shows no text.
// More than the free 10: a line and the Plus card (plus_view, place: diary). Every text from the API is a text node.
// One request: the free diary is one page. Only 401 "sign_in" means the session went (review I2); a 401 without JSON
// is the stage cookie — reload the page (spec §3); any other error — its line and "Try again" (review M18).
import { useEffect, useState } from 'preact/hooks';
import { fill, t, type DictKey } from '../../i18n';
import type { AccountApi, DiaryItem, Outcome } from '../../lib/accountApi';
import { cardById, cardImage } from '../../lib/deck';
import { DIARY_PAGE, entryHref, formatDate, isCrisis, kindKey } from '../../lib/diary';
import { errorMessageKey, needsHelpLink, reasonOf, type ErrorKind } from '../../lib/errors';
import { pagePath } from '../../lib/routes';
import type { Lang } from '../../lib/types';
import { HelpLine } from './HelpLine';
import { NoteIcon } from './icons';
import { PlusCard } from './PlusCard';

export const OUTCOME_KEYS: Record<Outcome, DictKey> = { yes: 'outcomeYes', partly: 'outcomePartly', no: 'outcomeNo' };

interface Props {
  lang: Lang;
  api: Pick<AccountApi, 'diary'>;
  onSignedOut: () => void; // 401 "sign_in": the session went
}

function Row({ item, lang }: { item: DiaryItem; lang: Lang }) {
  const d = t(lang);
  const crisis = isCrisis(item);
  return (
    <a class="diary-item" href={entryHref(lang, item.id)}>
      <span class="diary-item__meta">{formatDate(item.created_at, lang)} · {d[kindKey(item.kind, item.topic)]}</span>
      {crisis ? null : <span class="diary-item__question">{item.question ?? d.diaryNoQuestion}</span>}
      <span class="diary-item__cards" aria-hidden="true">
        {item.cards.map((c) => {
          const card = cardById(c.card_id);
          return card ? <img src={cardImage(card, 160)} alt="" width={32} height={55} class={c.reversed ? 'is-reversed' : undefined} /> : null;
        })}
      </span>
      {!crisis && item.headline ? <span class="diary-item__headline">{item.headline}</span> : null}
      <span class="diary-item__marks">
        {item.outcome ? <span class="diary-item__outcome">{d[OUTCOME_KEYS[item.outcome]]}</span> : null}
        {item.has_note ? <span class="diary-item__note"><NoteIcon /><span class="visually-hidden">{d.diaryNoteMark}</span></span> : null}
      </span>
    </a>
  );
}

export function DiaryList({ lang, api, onSignedOut }: Props) {
  const d = t(lang);
  const [items, setItems] = useState<DiaryItem[]>([]);
  const [hidden, setHidden] = useState(0);
  const [status, setStatus] = useState<'loading' | 'ready' | ErrorKind>('loading');

  const load = async () => {
    setStatus('loading');
    const result = await api.diary(undefined, DIARY_PAGE);
    if (!result.ok) {
      if (result.status === 401 && reasonOf(result.body) === 'sign_in') onSignedOut();
      else setStatus(result.error); // 'stage' for a 401 without JSON
      return;
    }
    setItems(result.data.items);
    setHidden(result.data.hidden_count);
    setStatus('ready');
  };

  useEffect(() => { void load(); }, []);

  return (
    <section class="diary__list" aria-busy={status === 'loading'}>
      {status === 'ready' && items.length === 0 ? (
        <div class="diary__empty">
          <p>{d.diaryEmpty}</p>
          <a class="btn btn--ink" href={pagePath('home', lang)}>{d.notFoundReading}</a>
        </div>
      ) : null}
      {items.length > 0 ? (
        <ul class="diary-list">
          {items.map((item) => <li key={item.id}><Row item={item} lang={lang} /></li>)}
        </ul>
      ) : null}
      {status !== 'loading' && status !== 'ready' ? (
        <div class="diary__error">
          <p role="alert">{d[errorMessageKey(status)]}</p>
          {needsHelpLink(status) ? <HelpLine lang={lang} /> : null}
          <button type="button" class="btn btn--outline" onClick={() => (status === 'stage' ? location.reload() : void load())}>
            {d.retry}
          </button>
        </div>
      ) : null}
      {hidden > 0 ? (
        <>
          <p class="diary__hidden">{fill(d.diaryHidden, { n: hidden })}</p>
          <PlusCard lang={lang} tool={null} place="diary" />
        </>
      ) : null}
    </section>
  );
}
