// The draw panel and its night room (spec 4.4a §4). Thin: state lives in src/lib/nightRoom.ts, requests in
// src/lib/readingFlow.ts, the page's choices in src/lib/panel.ts; here are only the DOM, timers, focus and history.
// History: the open room adds one entry with the same address (still no address of its own), so the phone's Back
// closes the room instead of leaving the page; × and Escape step back over that entry. Stage 4.4b §4: requests carry
// the token of a signed-in person (siteApi.ts); under a shown answer "Save to diary" opens the save sheet
// (useSaveToDiary.tsx). The open sheet has a history entry of its own above the room's (owner decision 14): Back
// closes only the sheet, and the room closing with the sheet open steps back over both entries at once.
import { useEffect, useMemo, useReducer, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import { analyticsEvent, sendEvent } from '../lib/analytics';
import { siteApi } from '../lib/siteApi';
import { CARD_BACK } from '../lib/deck';
import { CLOSED, DEAL_MS, FLIP_INTERVAL_MS, crisisPayloadOf, nightReducer, transitionEvents, type NightAction, type NightState } from '../lib/nightRoom';
import {
  ONE_CARD_ANCHOR, buildCreateBody, cardsFor, drawLabelKey, initialKind, panelConfig, situationKey, toolFor, type PanelPage,
} from '../lib/panel';
import { askFollowup, restoreReading, retryFollowup, startReading, streamReading, type FlowDeps } from '../lib/readingFlow';
import { newRequestId } from '../lib/requestId';
import { turnstileToken } from '../lib/turnstile';
import { SITUATIONS, type CardCount, type CrisisPayload, type Kind, type Lang, type Situation, type Tool } from '../lib/types';
import { NightRoom } from '../components/ui/NightRoom';
import { PlusCard } from '../components/ui/PlusCard';
import { useSaveToDiary } from '../components/ui/useSaveToDiary';
import { CheckIcon } from '../components/ui/icons';

interface Props {
  lang: Lang;
  page: PanelPage;
  cardId?: string;
  cardName?: string;
  showBacks?: boolean;
}

function timeZone(): string | undefined {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
  } catch {
    return undefined;
  }
}

function prefersReducedMotion(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export default function ReadingIsland({ lang, page, cardId, cardName, showBacks = false }: Props) {
  const d = t(lang);
  const config = useMemo(() => panelConfig(page, lang, cardId ?? null), [page, lang, cardId]);
  const [kind, setKind] = useState<Kind>(config.kind);
  const [count, setCount] = useState<CardCount>(1); // yes/no: one card by default (spec 4.5 §4)
  const [situation, setSituation] = useState<Situation | null>(null);
  const [question, setQuestion] = useState('');
  const [state, rawDispatch] = useReducer<NightState, NightAction>(nightReducer, CLOSED);
  const drawButton = useRef<HTMLButtonElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const run = useRef(0); // each draw is a run; a closed room ignores the late answers of its run
  const drawn = useRef({ at: 0, tz: undefined as string | undefined, question: '', id: '', tool: config.tool as Tool,
    cards: cardsFor(config.kind) as CardCount, signedIn: false });
  const previous = useRef<NightState>(CLOSED);
  const inHistory = useRef(false); // the room's history entry is on top
  const shownFor = useRef(0); // the run that already sent reading_shown
  const roomIsOpen = useRef(false);
  const focusQuestion = useRef(false); // "Ask another question": focus the question field once the room is closed
  const api = useMemo(() => siteApi(), []);
  const saving = useSaveToDiary({ lang, tool: drawn.current.tool, readingId: state.reading?.id ?? null,
    signedIn: drawn.current.signedIn });
  const inputId = `question-${page}`;

  useEffect(() => {
    const fromHash = () => setKind(initialKind(config, location.hash));
    fromHash();
    if (page !== 'card') sendEvent(analyticsEvent('tool_view', config.tool, lang));
    // a reload keeps history.state: the night room's entry (and the sheet's) of the page before it is dead now, and a
    // Back onto it would be swallowed by the room's own guard
    const stale = history.state as { arcanaNight?: boolean } | null;
    if (stale?.arcanaNight) history.replaceState(null, '');
    const onPop = () => {
      if (!inHistory.current) return; // our own step back: the flag dropped already
      // still on a room entry (a late step back of an earlier room landed there): the open room stays
      if ((history.state as { arcanaNight?: boolean } | null)?.arcanaNight) return;
      inHistory.current = false;
      if (roomIsOpen.current) closeNow();
    };
    window.addEventListener('popstate', onPop);
    // the footer link "Una carta" on this page; other hash changes (the skip link #main) leave the choice alone
    const onHash = () => { if (location.hash === ONE_CARD_ANCHOR) fromHash(); };
    if (config.countToggle) window.addEventListener('hashchange', onHash);
    return () => {
      window.removeEventListener('popstate', onPop);
      window.removeEventListener('hashchange', onHash);
    };
  }, []);

  const deps = (): FlowDeps => {
    const mine = run.current;
    return {
      api,
      dispatch: (action) => {
        if (run.current !== mine) {
          // owner decision 20.11.2026: a crisis answer that arrives after the room was closed still shows its help
          const payload = crisisPayloadOf(action);
          if (payload && !roomIsOpen.current && previous.current.phase !== 'limit') reopenForCrisis(payload);
          return;
        }
        if (action.type === 'created') {
          drawn.current.id = action.reading.id;
          drawn.current.signedIn = action.authed === true; // only a create request that carried the token saved it to the account
        }
        rawDispatch(action);
      },
      turnstileToken: async (sitekey) => { // a room closed during the check gets no token: the flow does not post
        const token = await turnstileToken(sitekey, { document, window });
        return run.current === mine ? token : null;
      },
      sleep: (ms) => new Promise((resolve) => setTimeout(() => { if (run.current === mine) resolve(); }, ms)), // a stale run never wakes
      reducedMotion: prefersReducedMotion(),
      newId: () => newRequestId(),
      now: () => Date.now(),
    };
  };

  // analytics on transitions: night_open, cards_revealed, reading_shown
  useEffect(() => {
    for (const name of transitionEvents(previous.current, state)) {
      if (name === 'reading_shown') { // once per drawn reading (not again after a fallback Retry)
        if (shownFor.current === run.current) continue;
        shownFor.current = run.current;
      }
      const params: Record<string, number> = name === 'cards_revealed' ? { cards_count: state.reading?.cards.length ?? 1 }
        : name === 'reading_shown' ? { ms_from_draw: Math.min(Math.max(Date.now() - drawn.current.at, 0), 600000) } : {};
      sendEvent(analyticsEvent(name, drawn.current.tool, lang, params));
    }
    const wasOpen = previous.current.phase !== 'closed' && previous.current.phase !== 'limit';
    const isOpen = state.phase !== 'closed' && state.phase !== 'limit';
    roomIsOpen.current = isOpen;
    if (wasOpen && !isOpen && state.phase === 'closed') {
      (focusQuestion.current ? input.current : drawButton.current)?.focus();
      focusQuestion.current = false;
    }
    if (wasOpen && !isOpen && inHistory.current) { // closed by the limit: drop the room's history entry
      stepBack();
    }
    if (state.phase === 'crisis' && previous.current.phase !== 'crisis') setQuestion(''); // "we haven't saved it"
    document.body.classList.toggle('is-locked', isOpen);
    previous.current = state;
  }, [state]);

  // the cards turn one after another (none of this with reduced motion: they arrive turned)
  useEffect(() => {
    if (state.phase !== 'reading' || !state.reading || state.revealed >= state.reading.cards.length) return;
    const timer = setTimeout(() => rawDispatch({ type: 'flip' }), state.revealed === 0 ? DEAL_MS : FLIP_INTERVAL_MS);
    return () => clearTimeout(timer);
  }, [state.phase, state.reading, state.revealed]);

  function reopenForCrisis(payload: CrisisPayload) {
    run.current += 1; // the late run is over
    drawn.current = { ...drawn.current, question: '', id: '' };
    setQuestion('');
    if (!inHistory.current) {
      history.pushState({ arcanaNight: true }, '');
      inHistory.current = true;
    }
    rawDispatch({ type: 'open' });
    rawDispatch({ type: 'crisis', payload });
    roomIsOpen.current = true;
  }

  const draw = (event: Event) => {
    event.preventDefault();
    if (roomIsOpen.current) return; // a bounced Enter or second click must not spend a second reading
    run.current += 1;
    const tz = timeZone();
    const body = buildCreateBody(config, { kind, question, situation, tz, count });
    drawn.current = { at: Date.now(), tz, question: body.question ?? '', id: '', tool: toolFor(config, kind), cards: cardsFor(kind, count), signedIn: false };
    sendEvent(analyticsEvent('draw_click', drawn.current.tool, lang, { has_question: Boolean(body.question), entry: config.entry }));
    if (!inHistory.current) {
      history.pushState({ arcanaNight: true }, '');
      inHistory.current = true;
    }
    rawDispatch({ type: 'open' });
    roomIsOpen.current = true;
    void startReading(deps(), body);
  };

  function closeNow() {
    run.current += 1;
    saving.closeForRoom(); // the sheet goes with the room; its history entry is handled in stepBack
    roomIsOpen.current = false; // at once: a late crisis before the next effect must still find the room closed
    rawDispatch({ type: 'close' });
  }

  // the single step back over the room's entry: the flag drops at once, so a second × or Escape cannot step twice
  function stepBack() {
    const steps = (inHistory.current ? 1 : 0) + saving.closeForRoom(); // the sheet's entry sits above the room's
    inHistory.current = false;
    if (steps === 1) history.back();
    else if (steps > 1) history.go(-steps);
  }

  const close = () => {
    stepBack();
    closeNow();
  };

  const askAnother = () => {
    focusQuestion.current = true;
    setQuestion('');
    close();
  };

  // always first without use_reading: after the free ones the API answers 402 confirm with the readings left (the
  // warning) or 402 plus, and only the confirmation sends use_reading: true
  const onFollowup = (text: string) =>
    void askFollowup(deps(), drawn.current.id, text, drawn.current.tz, false, state.followups.length);

  const roomOpen = state.phase !== 'closed' && state.phase !== 'limit';

  if (state.phase === 'limit') { // screen 11a: a day block, not the dark panel
    return (
      <div class="plus-slot" id={config.countToggle ? 'una-carta' : undefined}>
        <PlusCard lang={lang} tool={drawn.current.tool} focusOnShow />
      </div>
    );
  }

  return (
    <div class="night-panel" id={config.countToggle ? 'una-carta' : undefined}>
      <form class="field" onSubmit={draw}>
        {config.countToggle ? (
          <div class="chips" role="group" aria-label={d.countGroupLabel}>
            {(['one', 'three'] as const).map((k) => (
              <button type="button" class="chip" aria-pressed={kind === k} onClick={() => setKind(k)}>
                <CheckIcon />{k === 'one' ? d.oneCardChip : d.threeCardsChip}
              </button>
            ))}
          </div>
        ) : null}
        {config.yesNoCount ? (
          <>
            <div class="chips" role="group" aria-label={d.countGroupLabel}>
              {([1, 3] as const).map((n) => (
                <button type="button" class="chip" aria-pressed={count === n} onClick={() => setCount(n)}>
                  <CheckIcon />{n === 1 ? d.oneCardChip : d.threeCardsChip}
                </button>
              ))}
            </div>
            <p class="count-hint">{d.yesNoCountHint}</p>
          </>
        ) : null}
        {config.situations ? (
          <div class="field">
            <span id={`situation-${page}`} class="field__label">{d.situationLabel}</span>
            <div class="chips" role="group" aria-labelledby={`situation-${page}`}>
              {SITUATIONS.map((s) => (
                <button type="button" class="chip" aria-pressed={situation === s}
                  onClick={() => setSituation(situation === s ? null : s)}>
                  <CheckIcon />{d[situationKey(s)]}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <label for={inputId}>{d[config.labelKey]}</label>
        <input id={inputId} ref={input} class="input" type="text" maxLength={500} autocomplete="off"
          placeholder={d[config.placeholderKey]} value={question}
          onInput={(e) => setQuestion((e.target as HTMLInputElement).value)} />
        <p class="provider-line">{d.providerLine}</p>
        {showBacks ? (
          <div class="backs" aria-hidden="true">
            {Array.from({ length: cardsFor(kind, count) }, () => <img src={CARD_BACK} alt="" />)}
          </div>
        ) : null}
        <button type="submit" class="btn btn--gold btn--block" ref={drawButton}>{d[drawLabelKey(config, kind, count)]}</button>
        <p class="panel-hint">{d.freeSaveAfter}</p>
      </form>
      {roomOpen ? (
        <NightRoom
          state={state}
          lang={lang}
          config={config}
          threeCards={drawn.current.cards === 3}
          question={drawn.current.question}
          sourceName={cardName ?? null}
          onClose={close}
          onRetry={() => void streamReading(deps(), drawn.current.id, drawn.current.tz, 'retry')}
          onRestore={() => void restoreReading(deps(), drawn.current.id, drawn.current.tz)}
          onRestoreFollowup={() => {
            const lost = state.followups[state.followups.length - 1]?.lost;
            if (lost) void retryFollowup(deps(), drawn.current.id, drawn.current.tz, lost);
          }}
          onFollowup={onFollowup}
          onConfirmFollowup={() => state.confirm && void askFollowup(deps(), drawn.current.id, state.confirm.question, drawn.current.tz, true, state.followups.length)}
          onCancelFollowup={() => rawDispatch({ type: 'followupCancel' })}
          onMoreAbout={() => sendEvent(analyticsEvent('more_about_cards', drawn.current.tool, lang))}
          onAskAnother={askAnother}
          save={saving.slot}
          sheet={saving.sheet}
          onCloseSheet={saving.closeSheet}
        />
      ) : null}
    </div>
  );
}
