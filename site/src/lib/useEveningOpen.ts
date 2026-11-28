// The evening question opens at 17:00 local time (spec §2.3). A page left open from the afternoon must show it
// when the hour comes, so the gate is looked at again every minute and when the tab becomes visible again.
import { useEffect, useState } from 'preact/hooks';
import { eveningOpen } from './journal';

export const EVENING_CHECK_MS = 60_000;

export function useEveningOpen(): boolean {
  const [open, setOpen] = useState(() => eveningOpen(new Date()));
  useEffect(() => {
    const check = () => setOpen(eveningOpen(new Date()));
    const timer = setInterval(check, EVENING_CHECK_MS);
    document.addEventListener('visibilitychange', check);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', check);
    };
  }, []);
  return open;
}
