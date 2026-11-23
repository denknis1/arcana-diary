// "Save to diary" for a guest (screens 3, 3b; spec 4.4b §4): a sheet at the bottom of the night room with the
// "Remind me in 7 days" box (off) and the sign-in block. The return address carries the reading's one-time claim
// token, so the reading is saved on whatever device the e-mail link is opened. Closing it (×, Escape) keeps the
// answer on screen: the night room stays as it was. A claim token refused by the stage cookie (401 without JSON)
// sends nothing: the stage line and a reload button take the sign-in block's place (spec §3; final review M5).
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../i18n';
import { errorMessageKey } from '../../lib/errors';
import type { AccountApi } from '../../lib/accountApi';
import type { Auth } from '../../lib/auth';
import { returnUrl } from '../../lib/claim';
import type { Lang } from '../../lib/types';
import { CloseIcon } from './icons';
import { SignInBlock } from './SignInBlock';

const STAGE = Symbol('stage'); // the claim token was refused by the stage cookie

interface Props {
  lang: Lang;
  readingId: string;
  auth: Pick<Auth, 'sendLink' | 'google'> | null; // null until the page's Auth is ready (the library loads at the first send)
  google: boolean;
  accountApi: Pick<AccountApi, 'claimToken'>;
  origin: string;
  onClose: () => void;
  privacyHref?: string; // the privacy page, once it is open (spec stage 6 §6)
}

export function SaveSheet({ lang, readingId, auth, google, accountApi, origin, onClose, privacyHref }: Props) {
  const d = t(lang);
  const [remind, setRemind] = useState(false);
  const remindNow = useRef(remind);
  remindNow.current = remind;
  const title = useRef<HTMLHeadingElement>(null);
  const token = useRef<Promise<string | typeof STAGE | null> | null>(null);
  const [stage, setStage] = useState(false); // the stage cookie went: reload the page (spec §3)
  const reloadButton = useRef<HTMLButtonElement>(null);

  useEffect(() => title.current?.focus(), []);
  useEffect(() => { // the pressed button is gone with the sign-in block: the focus goes to the reload button
    if (stage) reloadButton.current?.focus();
  }, [stage]);

  // one token per open sheet, asked for at the first send; only a token that was made is kept, so "Send it again"
  // after a failure asks once more (review M13). Without one (409 already saved, 429, offline) the link still saves
  // the reading on this device: the sign-in started here, so the claim moves this device's guest readings. A 401
  // without JSON is the stage cookie, not "no token": nothing is sent, the page needs a reload (final review M5)
  const redirectTo = async () => {
    token.current ??= accountApi.claimToken(readingId).then((r) => {
      if (r.ok && r.data) return r.data.token;
      token.current = null;
      return !r.ok && r.error === 'stage' ? STAGE : null;
    });
    const claim = await token.current;
    if (claim === STAGE) {
      setStage(true);
      return null;
    }
    return { url: returnUrl(origin, lang, { claim, remind: remindNow.current }), thisDeviceOnly: claim === null };
  };

  return (
    <div class="sheet" role="dialog" aria-modal="true" aria-labelledby="save-title">
      <div class="sheet__top">
        <h2 id="save-title" class="sheet__title" tabIndex={-1} ref={title}>{d.saveTitle}</h2>
        <button type="button" class="close-button" aria-label={d.close} onClick={onClose}><CloseIcon /></button>
      </div>
      <p class="small">{d.saveLead}</p>
      <label class="check">
        <input type="checkbox" checked={remind} onChange={(e) => setRemind((e.target as HTMLInputElement).checked)} />
        <span>{d.saveRemind}</span>
      </label>
      {privacyHref ? <p class="small"><a href={privacyHref}>{d.privacyLink}</a></p> : null}
      {stage ? (
        <>
          <p role="alert">{d[errorMessageKey('stage')]}</p>
          <button type="button" class="btn btn--outline" ref={reloadButton} onClick={() => location.reload()}>{d.retry}</button>
        </>
      ) : auth ? (
        <SignInBlock lang={lang} auth={auth} google={google} idBase="save" redirectTo={redirectTo} surface="night" />
      ) : (
        <p class="small" role="status" aria-live="polite" />
      )}
    </div>
  );
}
