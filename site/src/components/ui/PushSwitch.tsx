// The account page's line about the morning reminder in this browser (stage 8.1 §2.5: "turned off there and in the
// account"). It reads the browser's own subscription and never registers anything; turning on stays under the card.
import { useEffect, useMemo, useState } from 'preact/hooks';
import { fill, t } from '../../i18n';
import { browserStorage, type StorageLike } from '../../lib/authState';
import { browserEnv, createPushApi, currentSubscription, hourLabel, pushSupport, storedHour, turnOff, type PushApi,
  type PushEnv } from '../../lib/push';
import { siteFetch } from '../../lib/siteApi';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  env?: PushEnv;
  api?: PushApi;
  storage?: StorageLike | null;
}

export function PushSwitch({ lang, env: givenEnv, api: givenApi, storage: givenStorage }: Props) {
  const d = t(lang);
  const env = useMemo(() => givenEnv ?? browserEnv(), []);
  const api = useMemo(() => givenApi ?? createPushApi(siteFetch()), []);
  const storage = givenStorage === undefined ? browserStorage() : givenStorage;
  const [on, setOn] = useState<boolean | null>(null);

  useEffect(() => {
    if (pushSupport(env) !== 'yes') return;
    void currentSubscription(env).then((subscription) => setOn(subscription !== null));
  }, []);

  if (on === null) return null;
  const hourShown = storedHour(storage); // null when this browser does not know the server's hour: just "On"
  return (
    <section class="account__push" aria-labelledby="account-push-title">
      <h2 id="account-push-title" class="h3">{d.accountPushTitle}</h2>
      {on ? (
        <p>
          {hourShown === null ? d.accountPushOnNoHour : fill(d.accountPushOn, { hour: hourLabel(hourShown, lang) })}{' '}
          <button type="button" class="btn btn--text" onClick={() => void turnOff({ env, api, storage }).then(() => setOn(false))}>
            {d.pushOff}
          </button>
        </p>
      ) : <p class="small">{d.accountPushNone}</p>}
    </section>
  );
}
