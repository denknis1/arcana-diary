// A one-time line on the home page (spec 4.4b §6): "Your account has been deleted." after the account page sent
// the person here — only with the mark that page left in sessionStorage (review M22); the address loses its
// ?account=deleted at once in any case.
import { useEffect, useState } from 'preact/hooks';
import { t } from '../i18n';
import { noticeOf, takeNotice, withoutNotice } from '../lib/notice';
import type { Lang } from '../lib/types';

export default function HomeNotice({ lang }: { lang: Lang }) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    // the live region is in the page empty from the start; its text comes a tick after mount, so it is announced
    const wanted = takeNotice(location.search) !== null; // the mark goes with any visit of the home page
    if (noticeOf(location.search)) history.replaceState(history.state, '', withoutNotice(location.href));
    if (!wanted) return;
    const timer = setTimeout(() => setShown(true), 0);
    return () => clearTimeout(timer);
  }, []);
  return <div class={shown ? 'notice notice--day' : undefined} role="status">{shown ? t(lang).accountDeleted : ''}</div>;
}
