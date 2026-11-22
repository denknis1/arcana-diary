// The diary page (screens 4a, 4b; spec 4.4b §5) on /diary and /es/diario. Static HTML, drawn here after load:
// sign-in off — "signing in opens soon"; not signed in — a line and the sign-in block (the person who comes back
// signs in right here, owner decision 3); signed in — once, the claim after sign-in (claim.ts), then the list or,
// with ?r=<id>, one entry. Nothing here runs at build time.
// The address hash is read before the sign-in library opens (it takes the session from `#access_token=…` and clears
// the hash): whether this page load finished a sign-in decides if `?claim=` / `remind=1` count (owner decision 15) —
// only when the library's session is the very token of the hash (final review I1: on a failed address login the
// library keeps the session the device had) — and `#error=…` is an expired link, whose hash goes once its line is
// shown (final review M3). A reminder that the sign-in switched on is said in one line with a link to the account
// page, where it can be turned off (owner decision 16).
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import { createAccountApi } from '../lib/accountApi';
import { sendEvent } from '../lib/analytics';
import { methodOf, openSession, type SessionStatus } from '../lib/auth';
import { browserStorage, clearSignedIn } from '../lib/authState';
import { finishSignIn, hashAccessToken, linkFailed, readReturnParams, returnUrl, type ConsentOutcome } from '../lib/claim';
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
  // consent: what the sign-in did to the reminder — 'set' says it is on, 'failed' that it is not (claim.ts)
  | { type: 'ready'; consent: ConsentOutcome; round: number; entry: string | null };

export default function DiaryIsland({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [view, setView] = useState<View>({ type: 'loading' });
  const api = useMemo(() => createAccountApi(siteFetch()), []);
  const reopened = useRef(false);
  // The access token of the address hash, read once, on the first open (undefined until then): "Try again" after a
  // failed claim is still the same page load; a re-open after the session went is not (handoff 3). The token alone
  // proves nothing: this page load finished a sign-in only if the library's session has exactly it (final review I1).
  const hashToken = useRef<string | null | undefined>(undefined);
  const rounds = useRef(0);

  const open = async () => {
    const hash = location.hash; // first: openSession() below lets the library clear it
    if (hashToken.current === undefined) hashToken.current = hashAccessToken(hash);
    const expired = linkFailed(hash);
    setView({ type: 'loading' });
    const status = await openSession();
    if (status.type !== 'signedIn') {
      // signedOut is a clean "no session" (auth.check() has cleared `ad_signed_in`, so the sign-in block's "only when
      // signed out" guard sets the started mark); a library error or a library that did not load is `unreachable`:
      // the try-again view, the flag kept
      setView({ type: 'status', status, expired });
      // the expired-link line is on screen: the #error=… goes from the address, so a reload does not show it again;
      // the query (claim, remind, r) stays for the sign-in here (final review M3)
      if (expired && status.type === 'signedOut') {
        history.replaceState(history.state, '', `${location.pathname}${location.search}`);
      }
      return;
    }
    const arrivedWithSession = hashToken.current !== null && status.session.access_token === hashToken.current;
    const finished = await finishSignIn({
      api, storage: browserStorage(), arrivedWithSession, href: location.href, lang,
      method: (started) => methodOf(status.session, started),
      replaceUrl: (url) => history.replaceState(history.state, '', url),
      send: sendEvent,
    });
    if (finished.type === 'error') setView({ type: 'failed', error: finished.error });
    else {
      rounds.current += 1;
      setView({
        type: 'ready', consent: finished.type === 'claimed' ? finished.consent : 'none', round: rounds.current,
        entry: entryParam(location.search),
      });
    }
  };

  useEffect(() => { void open(); }, []);
  useEffect(() => { // Back after a sign-out must not show the e-mail or an old list from the bfcache
    const onShow = (event: Event) => {
      if ((event as PageTransitionEvent).persisted) location.reload();
    };
    window.addEventListener('pageshow', onShow);
    return () => window.removeEventListener('pageshow', onShow);
  }, []);

  const signedOut = async () => { // a 401 "sign_in" in the middle: the session went on this device
    clearSignedIn();
    if (reopened.current) { // once per page: a second one shows "Try again", never a loop of requests (review I2)
      setView({ type: 'failed', error: 'other' });
      return;
    }
    reopened.current = true;
    hashToken.current = null; // the re-open finishes no sign-in of this page load
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
      {view.consent === 'set' ? <ReminderOn lang={lang} /> : null}
      {view.consent === 'failed' ? <p role="status">{d.diaryConsentFailed}</p> : null}
      {view.entry ? (
        <DiaryEntry key={view.round} lang={lang} id={view.entry} api={api} tz={deviceTimeZone()} onSignedOut={() => void signedOut()} />
      ) : (
        <DiaryList key={view.round} lang={lang} api={api} onSignedOut={() => void signedOut()} />
      )}
      <p><a class="diary__account" href={pagePath('account', lang)}>{d.diaryAccountLink}</a></p>
    </div>
  );
}

/** Owner decision 16: the sign-in switched the reminder on (`remind=1` of the link) — one line, the account page to
 * turn it off. The link sits inside the sentence: the dictionary's {account} is its place. */
function ReminderOn({ lang }: { lang: Lang }) {
  const d = t(lang);
  const [before, after = ''] = d.diaryReminderOn.split('{account}');
  return (
    <p role="status">
      {before}<a href={pagePath('account', lang)}>{d.diaryReminderOnLink}</a>{after}
    </p>
  );
}
