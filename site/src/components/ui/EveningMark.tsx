// The evening mark (stage 8.1 §2.3): "Did today's card show up in your day?" — Yes / Partly / No and one optional
// line of up to 280 characters. Under the Card of the Day from 17:00 and in the calendar for any past day. A guest
// (owner decision 56) sees the same question with inactive answers and a sign-in line, no note field, and nothing is
// sent. The mark and the line go only to PUT /api/daily/{day}; the event daily_felt says only where a first mark was
// set. Everything shown back is text.
import { useState } from 'preact/hooks';
import { t, type DictKey } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import type { ApiResult } from '../../lib/api';
import { DAILY_NOTE_MAX, type MarkPatch, type MarkSaved } from '../../lib/journal';
import { FELTS, type DailyMark, type Felt, type Lang } from '../../lib/types';

const FELT_KEYS: Record<Felt, DictKey> = { yes: 'feltYes', partly: 'feltPartly', no: 'feltNo' };

interface Props {
  lang: Lang;
  idBase: string;
  initial: DailyMark;
  place: 'daily' | 'calendar';
  surface: 'night' | 'day';
  save: (patch: MarkPatch) => Promise<ApiResult<MarkSaved>>;
  onSaved?: (saved: MarkSaved) => void;
  onSignedOut?: () => void;
  guest?: boolean;
}

type State = 'idle' | 'saving' | 'saved' | 'failed';

export function EveningMark({ lang, idBase, initial, place, surface, save, onSaved, onSignedOut, guest = false }: Props) {
  const d = t(lang);
  const [felt, setFelt] = useState<Felt | null>(initial.felt);
  const [note, setNote] = useState(initial.note ?? '');
  const [state, setState] = useState<State>('idle');
  const day = surface === 'day';

  const send = async (patch: MarkPatch): Promise<boolean> => {
    setState('saving');
    const result = await save(patch);
    if (result.ok) {
      setFelt(result.data.felt);
      setNote(result.data.note ?? '');
      setState('saved');
      onSaved?.(result.data);
      return true;
    }
    if (result.status === 401 && onSignedOut) onSignedOut();
    setState('failed');
    return false;
  };

  const pick = async (value: Felt) => {
    if (guest || state === 'saving') return;
    const first = felt === null;
    if ((await send({ felt: value })) && first) sendEvent(analyticsEvent('daily_felt', null, lang, { place }));
  };

  const saveNote = async (event: Event) => {
    event.preventDefault();
    if (state === 'saving') return;
    await send({ note: note.trim() === '' ? null : note });
  };

  return (
    <section class="evening" aria-labelledby={`${idBase}-question`}>
      <h3 id={`${idBase}-question`} class="evening__question">{d.eveningQuestion}</h3>
      <div class="chips" role="group" aria-labelledby={`${idBase}-question`}>
        {FELTS.map((value) => (
          <button key={value} type="button" class={day ? 'chip chip--day' : 'chip'} aria-pressed={felt === value}
            disabled={guest} aria-disabled={state === 'saving'} onClick={() => void pick(value)}>
            {d[FELT_KEYS[value]]}
          </button>
        ))}
      </div>
      {guest ? <p class="small">{d.eveningSignIn}</p> : (
      <form class="field evening__note" onSubmit={(e) => void saveNote(e)}>
        <label for={`${idBase}-note`}>{d.eveningNoteLabel}</label>
        <input id={`${idBase}-note`} type="text" class={day ? 'input input--day' : 'input'} maxLength={DAILY_NOTE_MAX}
          value={note} onInput={(e) => setNote((e.target as HTMLInputElement).value)} />
        <button type="submit" class="btn btn--outline" disabled={state === 'saving'}>{d.eveningNoteSave}</button>
      </form>
      )}
      <p class="small" role="status">{state === 'saved' ? d.eveningSaved : ''}</p>
      {state === 'failed' ? <p role="alert">{d.eveningFailed}</p> : null}
    </section>
  );
}
