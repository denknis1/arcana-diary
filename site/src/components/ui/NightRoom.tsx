// The night room (screens 2a–2e, 5b, 8b, 13d): a full-screen layer over the page with no address of its own.
// It only draws NightState (src/lib/nightRoom.ts) and calls back; requests and timers live in ReadingIsland.
// While cards are dealt: the positions on top, the question as the large title, the cards. With the answer (2e, 5b):
// the question small at top left, the headline as the large title; on a desktop cards left, text right (13d).
// Close: × and Escape (listened on the document, so it works wherever focus is); Tab stays inside; after an action
// whose button disappears, and on every change of phase, focus goes to the title. Yes/no on three cards (spec 4.5
// §4): under each card its own vote (icon and word), the verdict and "why" large in the text column. Under the answer
// (owner decision 41) "Save to diary" comes first (a guest: opens the save sheet inside this dialog; Escape then
// closes the sheet first, and the room behind it is inert) or "Saved to your diary ✓" with the link to the entry;
// below it a compact list of text links, one row per drawn card, that follow the launch rows of the stage 2 matrix
// for the tool (owner decision 38, drawnCardLink in src/lib/routes.ts); then "Back to …" and "Ask another question".
import type { ComponentChildren } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t, type DictKey } from '../../i18n';
import { answerBlocks } from '../../lib/answer';
import { CARD_BACK } from '../../lib/deck';
import { errorMessageKey, needsHelpLink } from '../../lib/errors';
import { handleDialogKey } from '../../lib/focus';
import { answerVisible, cardVotes, followupNow, lastFollowupLost, readingShown, statusKey, timedSpread, type NightState } from '../../lib/nightRoom';
import type { PanelConfig } from '../../lib/panel';
import { drawnCardLink } from '../../lib/routes';
import type { DrawnCard, Lang, Position, Vote } from '../../lib/types';
import { CardArt, CardName } from './CardFace';
import { CrisisView } from './CrisisView';
import { HelpLine } from './HelpLine';
import { CloseIcon, VerdictIcon } from './icons';
import { PlusCard } from './PlusCard';

export interface NightRoomProps {
  state: NightState;
  lang: Lang;
  config: PanelConfig;
  threeCards: boolean; // the drawn spread (not the page's default kind) picks the no-question title
  question: string;
  sourceName: string | null; // the card page's card, for "Back to The Moon"
  onClose: () => void;
  onRetry: () => void;
  onRestore: () => void;
  onRestoreFollowup: () => void;
  onFollowup: (question: string) => void;
  onConfirmFollowup: () => void;
  onCancelFollowup: () => void;
  onMoreAbout: () => void;
  onAskAnother: () => void;
  /** Spec 4.4b §4: null where sign-in is off (no button at all). */
  save?: SaveSlot | null;
  /** The open save sheet, drawn inside the dialog so that focus stays in the room. */
  sheet?: ComponentChildren;
  onCloseSheet?: () => void;
}

export interface SaveSlot {
  saved: boolean; // signed in: the reading is in the account already
  href: string; // the diary entry of this reading
  onSave: () => void;
}

const POSITION_KEYS: Record<Position, DictKey | null> = { past: 'posPast', present: 'posPresent', path: 'posPath', card: null };
const VOTE_KEYS: Record<Vote, DictKey> = { yes: 'voteYes', no: 'voteNo', unclear: 'voteUnclear' };

function cardLabel(card: DrawnCard, lang: Lang): string {
  const d = t(lang);
  const position = POSITION_KEYS[card.position];
  const name = card.reversed ? `${card.name}, ${d.reversedTag.toLowerCase()}` : card.name;
  return position ? `${d[position]} · ${name}` : name;
}

export function NightRoom(props: NightRoomProps) {
  const { state, lang, config } = props;
  const d = t(lang);
  const dialog = useRef<HTMLElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const onClose = useRef(props.onClose);
  onClose.current = props.onClose;
  const onCloseSheet = useRef(props.onCloseSheet);
  onCloseSheet.current = props.onCloseSheet;
  const saveButton = useRef<HTMLButtonElement>(null);
  const hadSheet = useRef(false);
  const [followupText, setFollowupText] = useState('');
  const lastPhase = useRef<string | null>(null);

  const reading = state.reading;
  const cards = reading?.cards ?? [];
  const three = cards.length === 3;
  // one row of text links per drawn card (owner decision 41), none on the card page: its card is the page itself
  const drawnRows = config.entry === 'card_page' ? [] : cards
    .map((card) => drawnCardLink(card, config.tool, lang, Boolean(reading?.verdict)))
    .filter((links) => links.length > 0);
  const timed = timedSpread(state); // past · present · path (not the three yes/no cards)
  const votes = cardVotes(state);
  const withAnswer = state.phase === 'reading' && answerVisible(state);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const sheet = dialog.current?.querySelector<HTMLElement>('.sheet');
      if (sheet && onCloseSheet.current) handleDialogKey(event, sheet, () => onCloseSheet.current?.());
      else if (dialog.current) handleDialogKey(event, dialog.current, () => onClose.current());
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  // the title takes focus on open, on every change of phase (a crisis answer is announced) and when the title
  // moves under the cards with the answer (the old element is gone)
  useEffect(() => {
    const active = document.activeElement;
    const lost = !active || active === document.body || !dialog.current?.contains(active);
    if (lastPhase.current !== state.phase || lost) title.current?.focus();
    lastPhase.current = state.phase;
  }, [state.phase, withAnswer]);

  // the sheet closed: focus goes back to "Save to diary"
  useEffect(() => {
    const open = Boolean(props.sheet);
    if (hadSheet.current && !open) saveButton.current?.focus();
    hadSheet.current = open;
  }, [Boolean(props.sheet)]);

  const then = (action: () => void) => () => {
    action();
    title.current?.focus(); // the button that was pressed disappears
  };

  const status = statusKey(state);
  const quoted = props.question ? `“${props.question}”` : props.threeCards ? d.noQuestionThree : d.noQuestionOne;
  const closeLabel = props.sourceName ? fill(d.closeBackTo, { name: props.sourceName }) : d.close;
  const top = withAnswer ? quoted : state.phase === 'reading' && timed ? [d.posPast, d.posPresent, d.posPath].join(' · ') : '';
  const heading = state.phase === 'crisis' && state.crisis ? state.crisis.crisis.title : quoted;
  const headline = state.answer.sections.headline?.trim();

  const submitFollowup = (event: Event) => {
    event.preventDefault();
    const text = followupText.trim();
    if (!text) return;
    props.onFollowup(text);
    setFollowupText('');
  };

  const spread = (small: boolean) => (
    <div class={`spread${three ? '' : ' spread--one'}${small ? ' spread--small' : ''}`}>
      {cards.map((card, i) => (
        <div class="spread__slot" key={card.card_id}>
          <div class={i < state.revealed ? 'flip is-turned' : 'flip'}>
            <div class="flip__inner">
              <div class="flip__side" aria-hidden="true"><img class="back" src={CARD_BACK} alt="" /></div>
              <div class="flip__side flip__side--face">
                {i < state.revealed ? (
                  <CardArt cardId={card.card_id} name={card.name} reversed={card.reversed} lang={lang}
                    sizes={small ? '(min-width: 900px) 128px, 78px' : three ? '106px' : '150px'} />
                ) : null}
              </div>
            </div>
          </div>
          {i < state.revealed ? <CardName cardId={card.card_id} name={card.name} /> : null}
          {timed ? <span class="spread__pos">{d[POSITION_KEYS[card.position]!]}</span> : null}
          {votes[i] ? (
            <span class="spread__vote"><VerdictIcon value={votes[i]!} size={20} />{d[VOTE_KEYS[votes[i]!]]}</span>
          ) : null}
        </div>
      ))}
    </div>
  );

  return (
    <div class="night-room">
      <section class="night" role="dialog" aria-modal="true" aria-labelledby="night-title" tabIndex={-1} ref={dialog}>
        <div class="night__top" inert={props.sheet ? true : undefined}>
          <p class="night__question">{top}</p>
          <button type="button" class="close-button" aria-label={closeLabel} onClick={props.onClose}>
            <CloseIcon />
          </button>
        </div>
        {withAnswer ? null : <h2 id="night-title" class="night__title" tabIndex={-1} ref={title}>{heading}</h2>}
        <p class={status === 'readingReady' || status === 'followupReady' ? 'visually-hidden' : 'night__status'}
          role="status" aria-live="polite">
          {status ? d[status] : ''}
        </p>

        {state.phase === 'opening' ? (
          <div class="deck-shuffle" aria-hidden="true"><img src={CARD_BACK} alt="" /></div>
        ) : null}

        {state.phase === 'reading' && reading && !withAnswer ? spread(false) : null}

        {withAnswer && reading ? (
          <div class="night__body" inert={props.sheet ? true : undefined}>
            <div class="night__cards">{spread(true)}</div>
            <div class="night__text">
              <h2 id="night-title" class="answer__headline" tabIndex={-1} ref={title}>{headline || quoted}</h2>
              {state.softLine ? <p class="answer__soft">{state.softLine}</p> : null}
              {reading.verdict ? (
                <div class="verdict">
                  <p class="verdict__word"><VerdictIcon value={reading.verdict.value} />{reading.verdict.label}</p>
                  {state.answer.sections.why ? <p>{d.whyPrefix} {state.answer.sections.why.trim()}</p> : null}
                </div>
              ) : null}
              {answerBlocks(state.answer, cards).map((block, i) => {
                if (block.kind === 'card') {
                  return (
                    <div key={i}>
                      <span class="answer__label">{cardLabel(block.card, lang)}</span>
                      <p class="answer__text">{block.text}</p>
                    </div>
                  );
                }
                if (block.kind === 'synthesis') return <p key={i} class="answer__synthesis">{block.text}</p>;
                if (block.kind === 'step') {
                  return (
                    <div key={i}>
                      <span class="answer__label">{d.stepLabel}</span>
                      <p class="answer__text">{block.text}</p>
                    </div>
                  );
                }
                return null; // the headline is the title; `why` is shown under the verdict
              })}
              {state.answer.replaced === 'fallback' && state.answer.retry && state.stream === 'done' ? (
                <button type="button" class="btn btn--outline" onClick={then(props.onRetry)}>{d.retry}</button>
              ) : null}
              {state.stream === 'lost' ? (
                <div class="night__actions">
                  <HelpLine lang={lang} />
                  <button type="button" class="btn btn--outline" onClick={then(props.onRestore)}>{d.retry}</button>
                </div>
              ) : null}
              {readingShown(state) ? (
                <Followups {...props} text={followupText} setText={setFollowupText} onSubmit={submitFollowup}
                  onConfirm={props.onConfirmFollowup} onRestoreFollowup={then(props.onRestoreFollowup)} onCancel={then(props.onCancelFollowup)} />
              ) : null}
              {readingShown(state) ? (
                <div class="night__actions">
                  {props.save ? (props.save.saved ? (
                    <p class="saved-mark"><a href={props.save.href}>{d.savedToDiary}</a></p>
                  ) : (
                    <button type="button" class="btn btn--gold" ref={saveButton} onClick={props.save.onSave}>{d.saveToDiary}</button>
                  )) : null}
                  {drawnRows.length > 0 ? (
                    <div class="more-cards">
                      {three ? <span class="answer__label" id="more-cards-label">{d.moreAbout}</span> : null}
                      <ul aria-labelledby={three ? 'more-cards-label' : undefined}>
                        {drawnRows.map((links, i) => (
                          <li key={i}>
                            {links.flatMap((link, j) => [
                              j > 0 ? <span key={`dot-${j}`} aria-hidden="true"> · </span> : null,
                              <a key={link.href} href={link.href} onClick={props.onMoreAbout}>{link.text}</a>,
                            ])}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {props.sourceName ? (
                    <button type="button" class="btn btn--gold" onClick={props.onClose}>{fill(d.backTo, { name: props.sourceName })}</button>
                  ) : null}
                  <button type="button" class="btn btn--text" onClick={props.onAskAnother}>{d.askAnother}</button>
                </div>
              ) : null}
              <p class="night__foot">{d.notGuarantee}</p>
            </div>
          </div>
        ) : null}

        {state.phase === 'reading' && !withAnswer && state.stream === 'lost' ? (
          <div class="night__actions">
            <HelpLine lang={lang} />
            <button type="button" class="btn btn--outline" onClick={then(props.onRestore)}>{d.retry}</button>
          </div>
        ) : null}

        {state.phase === 'crisis' && state.crisis ? <CrisisView payload={state.crisis} lang={lang} /> : null}

        {props.sheet ?? null}

        {state.phase === 'error' && state.error ? (
          <div class="night__actions">
            <p role="alert">{d[errorMessageKey(state.error)]}</p>
            {needsHelpLink(state.error) ? <HelpLine lang={lang} /> : null}
            {state.error === 'stage' ? (
              <button type="button" class="btn btn--gold" onClick={() => location.reload()}>{d.retry}</button>
            ) : (
              <button type="button" class="btn btn--outline" onClick={props.onClose}>{d.close}</button>
            )}
          </div>
        ) : null}
      </section>
    </div>
  );
}

interface FollowupProps extends NightRoomProps {
  text: string;
  setText: (text: string) => void;
  onSubmit: (event: Event) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

function Followups(props: FollowupProps) {
  const { state, lang, config } = props;
  const d = t(lang);
  const offer = followupNow(state);
  const confirmButton = useRef<HTMLButtonElement>(null);
  // the form unmounts when the API asks for confirmation: focus moves to the confirm button, so the notice
  // (role="alert") is announced and focus never falls to <body>
  useEffect(() => {
    if (state.confirm) confirmButton.current?.focus();
  }, [state.confirm]);
  // after "Use 1 reading and ask" the notice goes away: focus (and the scroll) go to the follow-up field, right under
  // the answer being written, not to the title at the top of the room (stage walk-through 20.11.2026)
  const focusFieldNext = useRef(false);
  const confirm = () => {
    focusFieldNext.current = true;
    props.onConfirm();
  };
  const counts = state.counts;
  const streaming = state.followups.some((f) => f.status === 'streaming');
  // the form stays mounted while an answer streams (its button is disabled), so focus never falls out of the room
  const formShown = !state.confirm && !state.followupPlus && state.answer.shown === 'model'
    && counts !== null && counts.followup_attempts_left > 0;
  // the form went away (the last attempt was used): if focus fell out of the room, the title takes it
  const wasShown = useRef(formShown);
  useEffect(() => {
    if (wasShown.current && !formShown) {
      const active = document.activeElement;
      const dialog = document.getElementById('night-title')?.closest('[role="dialog"]');
      if (!active || active === document.body || !dialog?.contains(active)) document.getElementById('night-title')?.focus();
    }
    if (formShown && focusFieldNext.current) {
      focusFieldNext.current = false;
      document.getElementById('followup-input')?.focus();
    }
    wasShown.current = formShown;
  }, [formShown]);
  const lastIsLost = lastFollowupLost(state); // a lost follow-up always shows the help line
  return (
    <section class="followups" aria-label={d.followupLabel}>
      {state.followups.map((f, i) => (
        <div key={i}>
          <p class="followup__q">{d.followupYouAsked}: {f.question}</p>
          {f.softLine ? <p class="answer__soft">{f.softLine}</p> : null}
          <p class="followup__a">{f.text}</p>
          {f.usedReading ? <p class="small">{d.followupUsedReading}</p> : null}
          {f.lost && f.status === 'failed' && i === state.followups.length - 1 ? (
            <button type="button" class="btn btn--outline" onClick={props.onRestoreFollowup}>{d.retry}</button>
          ) : null}
        </div>
      ))}
      {state.followupError || lastIsLost ? (
        <>
          {state.followupError ? <p role="alert">{d[errorMessageKey(state.followupError)]}</p> : null}
          {lastIsLost || (state.followupError && needsHelpLink(state.followupError)) ? <HelpLine lang={lang} /> : null}
        </>
      ) : null}
      {state.followupPlus ? <PlusCard lang={lang} tool={config.tool} focusOnShow /> : null}
      {state.confirm ? (
        <div class="notice" role="alert">
          <p>{fill(d.followupPaidWarning, { n: state.confirm.remaining })}</p>
          <div class="night__actions">
            <button type="button" class="btn btn--gold" ref={confirmButton} onClick={confirm}>{d.followupConfirm}</button>
            <button type="button" class="btn btn--text" onClick={props.onCancel}>{d.followupCancel}</button>
          </div>
        </div>
      ) : null}
      {formShown ? (
        <form class="followup-form" onSubmit={props.onSubmit}>
          <label for="followup-input" class="field__label">{d.followupLabel}</label>
          <input id="followup-input" class="input" maxLength={500} autocomplete="off" value={props.text}
            placeholder={d.followupPlaceholder} onInput={(e) => props.setText((e.target as HTMLInputElement).value)} />
          {offer === 'free' && counts ? <p class="small">{fill(d.followupFreeLeft, { n: counts.followups_left })}</p> : null}
          <button type="submit" class="btn btn--outline" disabled={streaming}>{d.followupSend}</button>
        </form>
      ) : counts && counts.followup_attempts_left <= 0 ? (
        <p class="small">{d.followupNone}</p>
      ) : null}
    </section>
  );
}
