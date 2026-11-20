// Cloudflare Turnstile, invisible (spec 4.2 §4.2, spec 4.4a §4): the script is loaded only after the API answered
// 403 {"reason": "turnstile", "sitekey": ...}; the site key comes from that answer (TURNSTILE_SITEKEY on the
// server), so the site holds no key of its own.

export const TURNSTILE_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
export const TOKEN_TIMEOUT_MS = 15000;

export interface TurnstileApi {
  render(container: HTMLElement, options: Record<string, unknown>): string | undefined;
  remove(widgetId: string): void;
}

export interface TurnstileHost {
  document: Pick<Document, 'createElement' | 'querySelector' | 'body' | 'head'>;
  window: { turnstile?: TurnstileApi; setTimeout: typeof setTimeout; clearTimeout: typeof clearTimeout };
}

let loading: Promise<TurnstileApi> | null = null;

/** Adds the script once; later calls share the same promise. */
export function loadTurnstile(host: TurnstileHost): Promise<TurnstileApi> {
  if (host.window.turnstile) return Promise.resolve(host.window.turnstile);
  if (loading) return loading;
  loading = new Promise<TurnstileApi>((resolve, reject) => {
    const script = host.document.createElement('script');
    script.src = TURNSTILE_SRC;
    script.async = true;
    script.onload = () => {
      if (host.window.turnstile) {
        resolve(host.window.turnstile);
      } else {
        loading = null;
        reject(new Error('turnstile missing'));
      }
    };
    script.onerror = () => {
      loading = null;
      reject(new Error('turnstile script failed'));
    };
    host.document.head.appendChild(script);
  });
  const attempt = loading;
  // A failed attempt must not stay cached (also covers onload firing before `loading` is assigned).
  attempt.catch(() => {
    if (loading === attempt) loading = null;
  });
  return attempt;
}

/** A token from an invisible widget, or null (script blocked, check failed, no answer in time). */
export async function turnstileToken(sitekey: string, host: TurnstileHost): Promise<string | null> {
  let api: TurnstileApi;
  try {
    api = await loadTurnstile(host);
  } catch {
    return null;
  }
  const container = host.document.createElement('div');
  container.className = 'turnstile-slot';
  host.document.body.appendChild(container);
  return new Promise<string | null>((resolve) => {
    let widgetId: string | undefined;
    let done = false;
    const finish = (token: string | null) => {
      if (done) return;
      done = true;
      host.window.clearTimeout(timer);
      if (widgetId) api.remove(widgetId);
      container.remove();
      resolve(token);
    };
    const timer = host.window.setTimeout(() => finish(null), TOKEN_TIMEOUT_MS);
    try {
      widgetId = api.render(container, {
        sitekey,
        callback: (token: string) => finish(token),
        'error-callback': () => finish(null),
        'timeout-callback': () => finish(null),
      });
    } catch {
      finish(null);
      return;
    }
    // The callback may have fired inside render, before the widget id was known.
    if (done && widgetId) api.remove(widgetId);
  });
}

/** For tests: forget the loaded script. */
export function resetTurnstileForTests(): void {
  loading = null;
}
