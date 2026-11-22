// The diary page (screens 4a, 4b; spec 4.4b §5) on /diary and /es/diario. Static HTML, drawn here after load:
// sign-in off — "signing in opens soon"; not signed in — a line and the sign-in block (the person who comes back
// signs in right here, owner decision 3); signed in — once, the claim after sign-in (claim.ts), then the list or,
// with ?r=<id>, one entry. Nothing here runs at build time.
// The address hash is read before the sign-in library opens (it takes the session from `#access_token=…` and clears
// the hash): whether this page load finished a sign-in decides if `?claim=` / `remind=1` count (owner decision 15),
// and `#error=…` is an expired link.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import { createAccountApi } from '../lib/accountApi';
import { sendEvent } from '../lib/analytics';
import { methodOf, openSession, type SessionStatus } from '../lib/auth';
import { browserStorage, clearSignedIn } from '../lib/authState';
import { finishSignIn, linkFailed, readReturnParams, returnUrl, signInCallbackInUrl } from '../lib/claim';
import { entryParam } from '../lib/diary';
import { errorMessageKey, needsHelpLink, type ErrorKind } from '../lib/errors';
import { pagePath } from '../lib/routes';
import { siteFetch } from '../lib/siteApi';
import { deviceTimeZone } from '../lib/timeZone';
import type { Lang } from '../lib/types';
import { DiaryEntry } from '../components/ui/DiaryEntry';
import { DiaryList } from '../components/ui/DiaryList';
import { HelpLine } from '../components/ui/HelpLine';
import { SignInBlock } from '../components/ui/SignInBlock';

type View =
  | { type: 'loading' }
  | { type: 'status'; status: Exclude<SessionStatus, { type: 'signedIn' }>; expired: boolean }
  | { type: 'failed'; error: ErrorKind } // the claim after sign-in did not go through
  // round: a new list (or entry) for each open, even when renders batch; entry: ?r=<id> of the address, else the list
  | { type: 'ready'; consentFailed: boolean; round: number; entry: string | null };

export default function DiaryIsland({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'loading' });
  const api = useMemo(() => createAccountApi(siteFetch()), []);
  const reopened = useRef(false);
  // Did this page load finish a sign-in (the session came in the address)? Read once, on the first open: "Try again"
  // after a failed claim is still the same page load; a re-open after the session went is not (handoff 3).
  const arrived = useRef<boolean | null>(null);
  const rounds = useRef(0);

  const open = async () => {
    const hash = location.hash; // first: openSession() below lets the library clear it
    arrived.current ??= signInCallbackInUrl(hash);
    const expired = linkFailed(hash);
    setView({ type: 'loading' });
    const status = await openSession();
    if (status.type !== 'signedIn') {
      // signedOut is a clean "no session" (auth.check() has cleared `ad_signed_in`, so the sign-in block's "only when
      // signed out" guard sets the started mark); a library error or a library that did not load is `unreachable`:
      // the try-again view, the flag kept
      setView({ type: 'status', status, expired });
      return;
    }
    const finished = await finishSignIn({
      api, storage: browserStorage(), arrivedWithSession: arrived.current, href: location.href, lang,
      method: (started) => methodOf(status.session, started),
      replaceUrl: (url) => history.replaceState(history.state, '', url),
      send: sendEvent,
    });
    if (finished.type === 'error') setView({ type: 'failed', error: finished.error });
    else {
      rounds.current += 1;
      setView({
        type: 'ready', consentFailed: finished.type === 'claimed' && finished.consent === 'failed', round: rounds.current,
        entry: entryParam(location.search),
      });
    }
  };

  useEffect(() => { void open(); }, []);

  const signedOut = async () => { // a 401 "sign_in" in the middle: the session went on this device
    clearSignedIn();
    if (reopened.current) { // once per page: a second one shows "Try again", never a loop of requests (review I2)
      setView({ type: 'failed', error: 'other' });
      return;
    }
    reopened.current = true;
    arrived.current = false; // the re-open finishes no sign-in of this page load
    await open();
  };

  if (view.type === 'loading') return <div class="diary" aria-busy="true" />; // no empty status line (review M18)
  if (view.type === 'failed') {
    return (
      <div class="diary">
        <p role="alert">{d[errorMessageKey(view.error)]}</p>
        {needsHelpLink(view.error) ? <HelpLine lang={lang} /> : null}
        {/* 'stage': the stage cookie went — reload the page (spec §3), do not claim again */}
        <button type="button" class="btn btn--outline"
          onClick={() => (view.error === 'stage' ? location.reload() : void open())}>{d.retry}</button>
      </div>
    );
  }
  if (view.type === 'status') {
    const { status } = view;
    if (status.type === 'off') return <div class="diary"><p class="lead">{d.diarySignInSoon}</p></div>;
    if (status.type === 'unreachable') {
      return (
        <div class="diary">
          <p role="alert">{d.errUnavailable}</p>
          <HelpLine lang={lang} />
          <button type="button" class="btn btn--outline" onClick={() => void open()}>{d.retry}</button>
        </div>
      );
    }
    // a link from the e-mail (or Google) brings back ?claim / ?remind: signing in here keeps them
    const keep = readReturnParams(location.search);
    return (
      <div class="diary diary--signin">
        <p class="lead">{d.diaryWhy}</p>
        {view.expired ? <p role="alert">{d.signInLinkExpired}</p> : null}
        <SignInBlock lang={lang} auth={status.auth} google={status.google} idBase="diary" surface="day"
          redirectTo={async () => {
            const back = new URL(returnUrl(location.origin, lang, keep)); // an entry's address comes back to it (M21)
            const entry = entryParam(location.search);
            if (entry) back.searchParams.set('r', entry);
            return back.toString();
          }} />
      </div>
    );
  }
  return (
    <div class="diary">
      {view.consentFailed ? <p role="status">{d.diaryConsentFailed}</p> : null}
      {view.entry ? (
        <DiaryEntry key={view.round} lang={lang} id={view.entry} api={api} tz={deviceTimeZone()} onSignedOut={() => void signedOut()} />
      ) : (
        <DiaryList key={view.round} lang={lang} api={api} onSignedOut={() => void signedOut()} />
      )}
      <p><a class="diary__account" href={pagePath('account', lang)}>{d.diaryAccountLink}</a></p>
    </div>
  );
}
