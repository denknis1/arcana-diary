// A one-time line on the home page after an action that left another page (spec 4.4b §6: "account deleted"). The
// address names the line; a mark in sessionStorage, left by the account page right before it goes, says that this
// browser really did it — a shared link with ?account=deleted alone shows nothing (review M22).
import type { StorageLike } from './authState';

export type Notice = 'accountDeleted';

export const NOTICE_PARAM = 'account';
export const NOTICE_KEY = 'ad_notice';

function sessionStore(): StorageLike | null {
  try {
    return typeof sessionStorage === 'undefined' ? null : sessionStorage;
  } catch {
    return null;
  }
}

export function noticeHref(home: string): string {
  return `${home}?${NOTICE_PARAM}=deleted`;
}

export function noticeOf(search: string): Notice | null {
  return new URLSearchParams(search).get(NOTICE_PARAM) === 'deleted' ? 'accountDeleted' : null;
}

export function markNotice(notice: Notice, storage: StorageLike | null = sessionStore()): void {
  try {
    storage?.setItem(NOTICE_KEY, notice);
  } catch {
    // without a storage the home page simply shows no line
  }
}

/** The address's notice, once, only when this browser left the mark; the mark goes in any case. */
export function takeNotice(search: string, storage: StorageLike | null = sessionStore()): Notice | null {
  const asked = noticeOf(search);
  try {
    const mine = storage?.getItem(NOTICE_KEY) ?? null;
    storage?.removeItem(NOTICE_KEY);
    return asked !== null && mine === asked ? asked : null;
  } catch {
    return null;
  }
}

/** The same address without the notice, for history.replaceState. */
export function withoutNotice(href: string): string {
  const url = new URL(href);
  url.searchParams.delete(NOTICE_PARAM);
  return `${url.pathname}${url.search}${url.hash}`;
}
