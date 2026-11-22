// The sign-in block (screens 3, 3b; spec 4.4b §3–§6): an e-mail for a link and, when it is on, "Continue with
// Google"; after the e-mail — "Check your e-mail" with "Send it again" after RESEND_WAIT_S seconds. The same block in
// the save sheet, the diary and the account page. Pressing either button marks this device (authState.ts), so the
// diary moves its guest readings into the account once after sign-in. "Use another e-mail" puts the focus back into
// the e-mail field (review M15). The mark is set only while the person is signed out (owner decision 15): a device
// that already has a sign-in (another tab) never marks, so a link opened there moves no guest readings.
import { useEffect, useRef, useState } from 'preact/hooks';
import { fill, t, type DictKey } from '../../i18n';
import type { Auth, SendError } from '../../lib/auth';
import { isSignedIn, markSignInStarted, type SignInMethod } from '../../lib/authState';
import type { Lang } from '../../lib/types';

export const RESEND_WAIT_S = 60;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MESSAGES: Record<SendError | 'invalid', DictKey> = {
  tooOften: 'signInTooOften', badEmail: 'plusEmailError', unavailable: 'errUnavailable', invalid: 'plusEmailError',
};

/** "Started here" only from a signed-out device, never from a signed-in surface (owner decision 15). */
function markStarted(method: SignInMethod): void {
  if (!isSignedIn()) markSignInStarted(method);
}

interface Props {
  lang: Lang;
  auth: Pick<Auth, 'sendLink' | 'google'>;
  google: boolean;
  idBase: string;
  /** Where the link and Google bring the person back (the save sheet adds the reading's claim token). */
  redirectTo: () => Promise<string>;
  /** 'night' inside the night room, 'day' on the diary and account pages. */
  surface: 'night' | 'day';
}

export function SignInBlock({ lang, auth, google, idBase, redirectTo, surface }: Props) {
  const d = t(lang);
  const [email, setEmail] = useState('');
  const [phase, setPhase] = useState<'form' | 'sending' | 'sent'>('form');
  const [error, setError] = useState<SendError | 'invalid' | null>(null);
  const [wait, setWait] = useState(0);
  const [resent, setResent] = useState(false);
  const sentTitle = useRef<HTMLHeadingElement>(null);
  const emailInput = useRef<HTMLInputElement>(null);
  const backToForm = useRef(false); // "Use another e-mail" was pressed
  const counting = wait > 0;

  useEffect(() => {
    if (!counting) return;
    const timer = setInterval(() => setWait((w) => Math.max(w - 1, 0)), 1000);
    return () => clearInterval(timer);
  }, [counting]);

  useEffect(() => { // the pressed button is gone: focus goes to what took its place
    if (phase === 'sent') sentTitle.current?.focus();
    else if (phase === 'form' && backToForm.current) emailInput.current?.focus();
    backToForm.current = false;
  }, [phase]);

  const send = async (again: boolean) => {
    const address = email.trim();
    if (!EMAIL.test(address)) {
      setError('invalid');
      return;
    }
    setError(null);
    setResent(false);
    if (!again) setPhase('sending');
    markStarted('email');
    const result = await auth.sendLink(address, await redirectTo());
    if (!result.ok) {
      setError(result.error);
      if (!again) setPhase('form');
      return;
    }
    setPhase('sent');
    setWait(RESEND_WAIT_S);
    setResent(again);
  };

  const withGoogle = async () => {
    setError(null);
    markStarted('google');
    const result = await auth.google(await redirectTo()); // on success the browser leaves for Google
    if (!result.ok) setError(result.error);
  };

  const message = error ? d[MESSAGES[error]] : null;
  const errorId = `${idBase}-error`;

  if (phase === 'sent') {
    return (
      <div class={`signin signin--${surface}`}>
        <h3 class="signin__title" tabIndex={-1} ref={sentTitle}>{d.checkEmailTitle}</h3>
        <p>{fill(d.checkEmailLead, { email: email.trim() })}</p>
        <button type="button" class="btn btn--outline" disabled={counting} onClick={() => void send(true)}>
          {d.checkEmailResend}
        </button>
        {counting ? <p class="small">{fill(d.checkEmailWait, { n: wait })}</p> : null}
        <p class="small" role="status">{resent ? d.checkEmailSent : ''}</p>
        {message ? <p role="alert">{message}</p> : null}
        <button type="button" class="btn btn--text" onClick={() => { backToForm.current = true; setPhase('form'); setWait(0); setError(null); }}>
          {d.checkEmailOther}
        </button>
      </div>
    );
  }

  return (
    <div class={`signin signin--${surface}`}>
      <form class="field" onSubmit={(event) => { event.preventDefault(); void send(false); }} noValidate>
        <label for={`${idBase}-email`}>{d.signInEmailLabel}</label>
        <input id={`${idBase}-email`} ref={emailInput} class={surface === 'day' ? 'input input--day' : 'input'} type="email"
          autocomplete="email" required maxLength={254} placeholder={d.plusEmailPlaceholder} value={email}
          aria-invalid={error ? 'true' : undefined} aria-describedby={message ? errorId : undefined}
          onInput={(e) => setEmail((e.target as HTMLInputElement).value)} />
        <button type="submit" class={surface === 'day' ? 'btn btn--ink' : 'btn btn--gold'} disabled={phase === 'sending'}>
          {d.signInSend}
        </button>
      </form>
      {google ? (
        <>
          <p class="signin__or">{d.signInOr}</p>
          <button type="button" class="btn btn--outline" onClick={() => void withGoogle()}>{d.signInGoogle}</button>
        </>
      ) : null}
      {message ? <p role="alert" id={errorId}>{message}</p> : null}
    </div>
  );
}
