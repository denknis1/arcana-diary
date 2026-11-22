// "Save to diary" for a guest (screens 3, 3b; spec 4.4b §4): a sheet at the bottom of the night room with the
// "Remind me in 7 days" box (off) and the sign-in block. The return address carries the reading's one-time claim
// token, so the reading is saved on whatever device the e-mail link is opened. Closing it (×, Escape) keeps the
// answer on screen: the night room stays as it was.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../../i18n';
import type { AccountApi } from '../../lib/accountApi';
import type { Auth } from '../../lib/auth';
import { returnUrl } from '../../lib/claim';
import type { Lang } from '../../lib/types';
import { CloseIcon } from './icons';
import { SignInBlock } from './SignInBlock';

interface Props {
  lang: Lang;
  readingId: string;
  auth: Pick<Auth, 'sendLink' | 'google'> | null; // null until the page's Auth is ready (the library loads at the first send)
  google: boolean;
  accountApi: Pick<AccountApi, 'claimToken'>;
  origin: string;
  onClose: () => void;
}

export function SaveSheet({ lang, readingId, auth, google, accountApi, origin, onClose }: Props) {
  const d = t(lang);
  const [remind, setRemind] = useState(false);
  const remindNow = useRef(remind);
  remindNow.current = remind;
  const title = useRef<HTMLHeadingElement>(null);
  const token = useRef<Promise<string | null> | null>(null);

  useEffect(() => title.current?.focus(), []);

  // one token per open sheet, asked for at the first send; only a token that was made is kept, so "Send it again"
  // after a failure asks once more (review M13). Without one (409 already saved, 429, offline) the link still saves
  // the reading on this device: the sign-in started here, so the claim moves this device's guest readings
  const redirectTo = async () => {
    token.current ??= accountApi.claimToken(readingId).then((r) => {
      if (r.ok && r.data) return r.data.token;
      token.current = null;
      return null;
    });
    return returnUrl(origin, lang, { claim: await token.current, remind: remindNow.current });
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
      {auth ? (
        <SignInBlock lang={lang} auth={auth} google={google} idBase="save" redirectTo={redirectTo} surface="night" />
      ) : (
        <p class="small" role="status" aria-live="polite" />
      )}
    </div>
  );
}
