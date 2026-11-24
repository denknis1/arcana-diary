// "Save to diary" in the night room (spec 4.4b §4): the button or "Saved to your diary ✓", the save sheet and its
// own history entry (owner decision 14: the phone's Back closes only the sheet), and save_click. ReadingIsland keeps
// the room and the room's history entry; this hook keeps the sheet's, so the wiring has a test of its own
// (useSaveToDiary.test.tsx, Fable plan review M20). The sign-in settings are read once a reading exists, so the
// button is there by the time the answer shows (review M14); the sign-in library loads only at the first send.
import type { ComponentChildren } from 'preact';
import { useEffect, useMemo, useRef, useState } from 'preact/hooks';
import { createAccountApi, type AccountApi } from '../../lib/accountApi';
import { analyticsEvent, sendEvent, type AnalyticsEvent } from '../../lib/analytics';
import { getAuth, type Auth } from '../../lib/auth';
import { authConfig, type AuthConfig } from '../../lib/authConfig';
import { entryHref } from '../../lib/diary';
import { SheetHistory, type HistoryLike } from '../../lib/sheetHistory';
import { siteFetch } from '../../lib/siteApi';
import type { Lang, Tool } from '../../lib/types';
import type { SaveSlot } from './NightRoom';
import { SaveSheet } from './SaveSheet';

export interface SaveToDiaryOptions {
  lang: Lang;
  tool: Tool;
  /** The reading in the room, once it is created. */
  readingId: string | null;
  /** The create request carried the token: the reading is in the account already. */
  signedIn: boolean;
  /** Tests pass their own; the page uses the real ones. */
  readConfig?: () => Promise<AuthConfig | null>;
  loadAuth?: () => Promise<Auth | null>;
  accountApi?: Pick<AccountApi, 'claimToken'>;
  history?: HistoryLike;
  send?: (event: AnalyticsEvent) => void;
  origin?: string;
  /** The privacy page next to the reminder consent, once it is open (spec stage 6 §6). */
  privacyHref?: string;
  termsHref?: string;
}

export interface SaveToDiary {
  /** NightRoom `save`: null where sign-in is off or no reading is made yet. */
  slot: SaveSlot | null;
  /** NightRoom `sheet`. */
  sheet: ComponentChildren;
  /** NightRoom `onCloseSheet` (Escape inside the sheet). */
  closeSheet: (() => void) | undefined;
  /** The room is closing: the sheet goes too, without a step of its own; 1 when the sheet's history entry was still
   * on top (ReadingIsland then steps back over it together with the room's entry), else 0. */
  closeForRoom: () => number;
}

export function useSaveToDiary(options: SaveToDiaryOptions): SaveToDiary {
  const { lang, tool, readingId, signedIn, readConfig = authConfig, loadAuth = getAuth, send = sendEvent } = options;
  const [config, setConfig] = useState<AuthConfig | null>(null); // null: not read yet, or could not be read
  const [open, setOpen] = useState(false);
  const [auth, setAuth] = useState<Auth | null>(null);
  const api = useMemo(() => options.accountApi ?? createAccountApi(siteFetch()), []);
  const entry = useRef<SheetHistory | null>(null);
  const browserHistory = (): HistoryLike => options.history ?? window.history; // not at build time: Astro renders this
  const sheetEntry = () => (entry.current ??= new SheetHistory(browserHistory()));

  useEffect(() => {
    if (readingId && config === null) void readConfig().then(setConfig);
  }, [readingId]);

  useEffect(() => {
    const onPop = () => {
      if (sheetEntry().popped(browserHistory().state)) setOpen(false); // Back left the sheet's entry: the room stays
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const openSheet = () => {
    send(analyticsEvent('save_click', tool, lang));
    sheetEntry().push();
    setOpen(true);
    void loadAuth().then(setAuth); // the page's Auth; the library itself loads at the first send
  };

  const closeSheet = () => {
    if (sheetEntry().consume()) browserHistory().back(); // × and Escape: the sheet's entry goes, exactly once
    setOpen(false);
  };

  const closeForRoom = () => {
    setOpen(false);
    return sheetEntry().consume();
  };

  const slot = config?.enabled && readingId ? { saved: signedIn, href: entryHref(lang, readingId), onSave: openSheet } : null;
  const sheet = open && config && readingId ? (
    <SaveSheet lang={lang} readingId={readingId} auth={auth} google={config.google} accountApi={api}
      origin={options.origin ?? location.origin} onClose={closeSheet} privacyHref={options.privacyHref} termsHref={options.termsHref} />
  ) : null;
  return { slot, sheet, closeSheet: open ? closeSheet : undefined, closeForRoom };
}
