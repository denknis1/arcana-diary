// "Remind me each morning" under the Card of the Day (stage 8.1 §2.5): shown quietly after the third day in a row,
// with the hour (8:00 by default, local time); on an iPhone or iPad outside the Home Screen app, the hint how to add
// the site there instead. Once on, the same place says so and turns it off. "Not now" hides the offer on this device
// for DISMISS_DAYS. Nothing is registered or asked before the person presses the button.
import { useEffect, useMemo, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import { analyticsEvent, sendEvent } from '../../lib/analytics';
import { browserStorage, type StorageLike } from '../../lib/authState';
import { localIsoDay } from '../../lib/daily';
import {
  browserEnv, createPushApi, currentSubscription, DEFAULT_HOUR, DISMISSED_KEY, hourLabel, OFFER_STREAK, offerDismissed,
  pushSupport, refresh, storedHour, turnOff, turnOn, type PushApi, type PushEnv,
} from '../../lib/push';
import { siteFetch } from '../../lib/siteApi';
import { deviceTimeZone } from '../../lib/timeZone';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  streak: number;
  env?: PushEnv;
  api?: PushApi;
  storage?: StorageLike | null;
  now?: () => number;
}

type State = 'checking' | 'offer' | 'busy' | 'on' | 'denied' | 'failed' | 'hidden';

const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

export function PushOffer({ lang, streak, env: givenEnv, api: givenApi, storage: givenStorage, now = Date.now }: Props) {
  const d = t(lang);
  const env = useMemo(() => givenEnv ?? browserEnv(), []);
  const api = useMemo(() => givenApi ?? createPushApi(siteFetch()), []);
  const storage = givenStorage === undefined ? browserStorage() : givenStorage;
  const support = pushSupport(env);
  const [state, setState] = useState<State>('checking');
  const [hour, setHour] = useState(DEFAULT_HOUR);
  const deps = () => ({ env, api, storage, lang, tz: deviceTimeZone(), today: localIsoDay(new Date(now())) });

  useEffect(() => {
    if (support !== 'yes') return setState('offer');
    void currentSubscription(env).then((subscription) => {
      if (subscription && env.notification?.permission === 'granted') {
        setHour(storedHour(storage));
        setState('on');
        void refresh(deps(), subscription);
      } else setState(env.notification?.permission === 'denied' ? 'denied' : 'offer');
    });
  }, []);

  if (support === 'no' || state === 'checking' || state === 'hidden') return null;
  if (state === 'on') {
    return (
      <p class="small push">
        {fill(d.pushOn, { hour: hourLabel(hour, lang) })}{' '}
        <button type="button" class="btn btn--text" onClick={() => void turnOff(deps()).then(() => setState('offer'))}>
          {d.pushOff}
        </button>
      </p>
    );
  }
  if (streak < OFFER_STREAK || offerDismissed(now(), storage)) return null;

  const dismiss = () => {
    storage?.setItem(DISMISSED_KEY, String(now()));
    setState('hidden');
  };
  const notNow = <button type="button" class="btn btn--text" onClick={dismiss}>{d.pushNotNow}</button>;

  if (support === 'ios-home') return <div class="push"><p class="small">{d.pushIosHint}</p>{notNow}</div>;
  if (state === 'denied') return <p class="small push">{d.pushDenied}</p>;

  const enable = async () => {
    if (state === 'busy') return;
    setState('busy');
    const result = await turnOn(deps(), hour);
    if (result === 'on') sendEvent(analyticsEvent('push_enabled', 'daily', lang));
    setState(result === 'on' ? 'on' : result === 'denied' ? 'denied' : result === 'off' ? 'hidden' : 'failed');
  };

  return (
    <div class="push">
      <label for="push-hour">{d.pushHourLabel}</label>
      <select id="push-hour" class="input push__hour" value={String(hour)}
        onChange={(e) => setHour(Number((e.target as HTMLSelectElement).value))}>
        {HOURS.map((h) => <option key={h} value={String(h)}>{hourLabel(h, lang)}</option>)}
      </select>
      <button type="button" class="btn btn--outline" aria-disabled={state === 'busy'} onClick={() => void enable()}>
        {d.pushOffer}
      </button>
      {notNow}
      {state === 'failed' ? <p role="alert" class="small">{d.pushFailed}</p> : null}
    </div>
  );
}
