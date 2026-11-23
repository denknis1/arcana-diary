// The account page (spec 4.4b §6) on /account and /es/cuenta: sign-in off — "signing in opens soon"; the sign-in
// library errs or does not load — "try again", the `ad_signed_in` flag kept (handoff 9); not signed in — the sign-in
// block of the diary; signed in — the e-mail, readings left today, "Sign out"; the consent to "did it come true?"
// e-mails (they start later); "Download my readings"; "Delete account" with the "Delete forever?" dialog. After the
// deletion this device signs out at once (api/README.md "Передача в 4.4") and goes to the home page, which says the
// account is deleted — once, by a mark this page leaves in sessionStorage (review M22). A sign-out that hangs never
// holds the person here: after SIGN_OUT_WAIT_MS the page goes on (auth-js drops the local session before its
// request, and Auth.signOut clears the flags first — review M6).
// Actions (handoff 10): nothing changes on screen before the API says so; a failure is said next to the action that
// failed (inside the dialog for the dialog's buttons); while an action runs, the buttons are aria-disabled and
// ignore presses, so the focus stays. Only 401 {"reason": "sign_in"} means the session went: the sign-in block. A
// 401 without JSON is the stage cookie: the line and a button that reloads the page. Every API text is a text node.
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { fill, t } from '../i18n';
import { createAccountApi, type Account, type AccountApi } from '../lib/accountApi';
import { openSession, type Auth, type SessionStatus } from '../lib/auth';
import { clearSignedIn } from '../lib/authState';
import { returnUrl } from '../lib/claim';
import { saveFile, type SaveFile } from '../lib/download';
import { errorMessageKey, needsHelpLink, reasonOf, type ErrorKind } from '../lib/errors';
import { markNotice, noticeHref } from '../lib/notice';
import { pagePath } from '../lib/routes';
import { siteFetch } from '../lib/siteApi';
import { deviceTimeZone } from '../lib/timeZone';
import type { Lang } from '../lib/types';
import { DeleteAccountDialog } from '../components/ui/DeleteAccountDialog';
import { HelpLine } from '../components/ui/HelpLine';
import { SignInBlock } from '../components/ui/SignInBlock';

export const SIGN_OUT_WAIT_MS = 3000;

type Action = 'consent' | 'export' | 'delete' | 'signOut';

type View =
  | { type: 'loading' }
  | { type: 'status'; status: Exclude<SessionStatus, { type: 'signedIn' }> }
  | { type: 'failed'; error: ErrorKind; auth: Auth } // the account could not be read; signing out stays possible
  | { type: 'ready'; auth: Auth; google: boolean; account: Account };

/** 401 {"reason": "sign_in"}: the session went on this device (spec 4.4b §3). */
function sessionGone(status: number, body: unknown): boolean {
  return status === 401 && reasonOf(body) === 'sign_in';
}

/** A line for what went wrong: the help line only where the message needs it; the stage cookie reloads the page
 * (spec §3); `retry` asks again. */
function Problem({ error, lang, retry }: { error: ErrorKind; lang: Lang; retry?: () => void }) {
  const d = t(lang);
  const again = error === 'stage' ? () => location.reload() : retry;
  return (
    <div class="account__error">
      <p role="alert">{d[errorMessageKey(error)]}</p>
      {needsHelpLink(error) ? <HelpLine lang={lang} /> : null}
      {again ? <button type="button" class="btn btn--outline" onClick={again}>{d.retry}</button> : null}
    </div>
  );
}

interface Props {
  lang: Lang;
  /** The privacy page under the consent, once it is open (spec stage 6 §6). */
  privacyHref?: string;
  /** Tests pass their own; the page uses the real ones. */
  api?: AccountApi;
  save?: SaveFile;
  navigate?: (url: string) => void;
  session?: () => Promise<SessionStatus>;
  signOutWaitMs?: number;
}

export default function AccountIsland({ lang, privacyHref, api: given, save = saveFile, navigate = (url) => location.assign(url),
  session = openSession, signOutWaitMs = SIGN_OUT_WAIT_MS }: Props) {
  const d = t(lang);
  const api = useMemo(() => given ?? createAccountApi(siteFetch()), []);
  const [view, setView] = useState<View>({ type: 'loading' });
  const [failed, setFailed] = useState<{ action: Action; error: ErrorKind } | null>(null);
  const [dialog, setDialog] = useState(false);
  const [busy, setBusy] = useState<Action | null>(null);
  const busyNow = useRef<Action | null>(null); // the press is ignored while another action runs
  const deleteButton = useRef<HTMLButtonElement>(null);
  const hadDialog = useRef(false);
  const home = pagePath('home', lang);

  const signedOut = (auth: Auth, google: boolean) => { // clears the flag, so the block's "started here" mark is set
    clearSignedIn();
    setDialog(false);
    setView({ type: 'status', status: { type: 'signedOut', auth, google } });
  };

  const load = async () => {
    setView({ type: 'loading' });
    const opened = await session();
    if (opened.type !== 'signedIn') {
      setView({ type: 'status', status: opened }); // `unreachable` keeps the flag: try again, never the sign-in block
      return;
    }
    const result = await api.account(deviceTimeZone());
    if (result.ok) setView({ type: 'ready', auth: opened.auth, google: opened.google, account: result.data });
    else if (sessionGone(result.status, result.body)) signedOut(opened.auth, opened.google);
    else setView({ type: 'failed', error: result.error, auth: opened.auth }); // 'stage' for a 401 without JSON: the line and a reload
  };

  useEffect(() => { void load(); }, []);
  useEffect(() => { // Back after a sign-out or a deletion must not show the e-mail or a frozen dialog from the bfcache
    const onShow = (event: Event) => {
      if ((event as PageTransitionEvent).persisted) location.reload();
    };
    window.addEventListener('pageshow', onShow);
    return () => window.removeEventListener('pageshow', onShow);
  }, []);
  useEffect(() => { // the dialog is gone: focus goes back to the button that opened it
    if (hadDialog.current && !dialog) deleteButton.current?.focus();
    hadDialog.current = dialog;
  }, [dialog]);

  const leave = async (auth: Auth, url: string) => { // sign out on this device at once, then go; a hung sign-out waits at most
    await Promise.race([auth.signOut().catch(() => {}), new Promise<void>((resolve) => setTimeout(resolve, signOutWaitMs))]);
    navigate(url);
  };

  if (view.type === 'loading') return <div class="account" aria-busy="true" />; // no empty status line (review M18)
  if (view.type === 'failed') {
    const { auth } = view;
    return (
      <div class="account">
        <Problem error={view.error} lang={lang} retry={() => void load()} />
        <div class="account__actions">
          <button type="button" class="btn btn--ink" aria-disabled={busy !== null} onClick={() => {
            if (busyNow.current) return;
            busyNow.current = 'signOut';
            setBusy('signOut');
            void leave(auth, home); // busy until the page goes
          }}>{d.accountSignOut}</button>
        </div>
      </div>
    );
  }
  if (view.type === 'status') {
    const { status } = view;
    if (status.type === 'off') return <div class="account"><p class="lead">{d.diarySignInSoon}</p></div>;
    if (status.type === 'unreachable') {
      return (
        <div class="account">
          <p role="alert">{d.errUnavailable}</p>
          <HelpLine lang={lang} />
          <button type="button" class="btn btn--outline" onClick={() => void load()}>{d.retry}</button>
        </div>
      );
    }
    return (
      <div class="account">
        <SignInBlock lang={lang} auth={status.auth} google={status.google} idBase="account" surface="day"
          redirectTo={async () => returnUrl(location.origin, lang)} />
      </div>
    );
  }

  const { auth, google, account } = view;

  const start = (action: Action): boolean => {
    if (busyNow.current) return false;
    busyNow.current = action;
    setBusy(action);
    return true;
  };
  const finish = () => {
    busyNow.current = null;
    setBusy(null);
  };

  const toggle = async (box: HTMLInputElement) => {
    const wanted = box.checked;
    box.checked = account.reminders_consent; // no optimistic update: the switch moves when the API has saved it
    if (!start('consent')) return;
    let result: Awaited<ReturnType<AccountApi['setConsent']>>;
    try {
      result = await api.setConsent(wanted);
    } finally {
      finish();
    }
    if (!result.ok) {
      if (sessionGone(result.status, result.body)) return signedOut(auth, google);
      return setFailed({ action: 'consent', error: result.error });
    }
    setFailed(null);
    setView({ type: 'ready', auth, google, account: { ...account, reminders_consent: result.data.reminders_consent,
      consent_at: result.data.consent_at } });
  };

  const download = async () => {
    if (!start('export')) return;
    let file: Awaited<ReturnType<AccountApi['exportFile']>>;
    try {
      file = await api.exportFile();
    } finally {
      finish();
    }
    if (file.ok) {
      setFailed(null);
      save(file.blob, file.filename);
    } else if (file.status === 401 && file.error !== 'stage') {
      signedOut(auth, google); // a 401 with a JSON reason that authFetch hands back is "sign_in" (api/routes/common.py)
    } else setFailed({ action: 'export', error: file.error });
  };

  const signOut = async () => {
    if (!start('signOut')) return;
    await leave(auth, home); // busy until the page goes
  };

  const remove = async () => {
    if (!start('delete')) return;
    setFailed(null);
    let result: Awaited<ReturnType<AccountApi['deleteAccount']>>;
    try {
      result = await api.deleteAccount();
    } catch (error) {
      finish();
      throw error;
    }
    if (!result.ok) {
      finish();
      if (sessionGone(result.status, result.body)) return signedOut(auth, google);
      return setFailed({ action: 'delete', error: result.error }); // said inside the dialog (review I5)
    }
    markNotice('accountDeleted');
    await leave(auth, noticeHref(home)); // at once: the token still lives until it expires; busy until the page goes
  };

  const openDialog = () => {
    if (busyNow.current) return;
    setFailed(null);
    setDialog(true);
  };
  const closeDialog = () => {
    setDialog(false);
    setFailed(null);
  };

  const inDialog = dialog && (failed?.action === 'export' || failed?.action === 'delete');
  const problem = (action: Action) => (failed?.action === action && !dialog ? <Problem error={failed.error} lang={lang} /> : null);

  return (
    <div class="account">
      {account.email ? <p>{fill(d.accountEmail, { email: account.email })}</p> : null}
      <p>{fill(d.accountLeft, { n: account.remaining, limit: account.limit })}</p>
      <div class="account__consent">
        <label class="check check--day">
          <input type="checkbox" checked={account.reminders_consent} aria-describedby="account-consent-note"
            aria-disabled={busy !== null} onChange={(e) => void toggle(e.currentTarget as HTMLInputElement)} />
          <span>{d.accountConsent}</span>
        </label>
        <p id="account-consent-note" class="small muted">{d.accountConsentNote}</p>
        {privacyHref ? <p class="small"><a href={privacyHref}>{d.privacyLink}</a></p> : null}
        {problem('consent')}
      </div>
      <div class="account__actions">
        <button type="button" class="btn btn--outline" aria-disabled={busy !== null} onClick={() => void download()}>
          {d.accountExport}
        </button>
        <a class="btn btn--outline" href={pagePath('diary', lang)}>{d.navDiary}</a>
        <button type="button" class="btn btn--ink" aria-disabled={busy !== null} onClick={() => void signOut()}>
          {d.accountSignOut}
        </button>
        <button type="button" class="btn btn--text" ref={deleteButton} aria-disabled={busy !== null} onClick={openDialog}>
          {d.accountDelete}
        </button>
      </div>
      {problem('export')}
      {dialog ? (
        <DeleteAccountDialog lang={lang} busy={busy !== null} error={inDialog && failed ? d[errorMessageKey(failed.error)] : null}
          onReload={failed?.error === 'stage' ? () => location.reload() : undefined}
          onDownload={() => void download()} onDelete={() => void remove()} onCancel={closeDialog} />
      ) : null}
    </div>
  );
}
