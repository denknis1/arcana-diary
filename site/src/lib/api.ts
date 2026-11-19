// The API calls of the reading screens (api/README.md "Адреса"). Same origin, path /api; the guest cookie goes
// with every request. Streams are read through fetch (spec 4.4a §4). Nothing here touches the page.
import { classifyError, type ErrorKind } from './errors';
import { followupRefusal, type FollowupBody, type FollowupRefusal } from './followups';
import { readSse, STREAM_IDLE_MS, type SseEvent } from './sse';
import type { CreateBody, CrisisPayload, DailyCard, Lang, ReadingCreated, ReadingView } from './types';

export type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: ErrorKind; body: Record<string, unknown> | null };

export type CreateResult =
  | { type: 'reading'; reading: ReadingCreated }
  | { type: 'crisis'; payload: CrisisPayload }
  | { type: 'error'; error: ErrorKind; body: Record<string, unknown> | null };

/** ended — the body ended (with or without `done`); broken — the connection failed mid-way. */
export type StreamEnd =
  | { type: 'ended' }
  | { type: 'broken' }
  | { type: 'error'; error: ErrorKind; body: Record<string, unknown> | null };

export type FollowupResult = { type: 'stream'; end: StreamEnd } | { type: 'refused'; refusal: FollowupRefusal };

export interface Api {
  createReading(body: CreateBody): Promise<CreateResult>;
  streamReading(id: string, tz: string | undefined, onEvent: (event: SseEvent) => void): Promise<StreamEnd>;
  retryReading(id: string, tz: string | undefined, onEvent: (event: SseEvent) => void): Promise<StreamEnd>;
  getReading(id: string, tz: string | undefined): Promise<ApiResult<ReadingView>>;
  postFollowup(id: string, body: FollowupBody, onEvent: (event: SseEvent) => void): Promise<FollowupResult>;
  getDaily(lang: Lang, tz: string | undefined): Promise<ApiResult<DailyCard>>;
  joinWaitlist(email: string, lang: Lang): Promise<ApiResult<{ ok: boolean }>>;
}

const JSON_HEADERS = { 'content-type': 'application/json' };

export function withQuery(path: string, params: Record<string, string | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}

function readingPath(id: string, tail = ''): string {
  return `/api/readings/${encodeURIComponent(id)}${tail}`;
}

async function jsonBody(response: Response): Promise<Record<string, unknown> | null> {
  try {
    const body = await response.json();
    return body && typeof body === 'object' ? (body as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

function isStream(response: Response): boolean {
  return response.ok && response.body !== null && (response.headers.get('content-type') ?? '').includes('text/event-stream');
}

export interface ApiOptions {
  /** Silence on a stream, in ms, after which the request is aborted and counts as broken. */
  idleMs?: number;
}

/** An abort signal that fires when nothing happened for `idleMs`; `touch` re-arms it, `stop` ends it for good. */
function idleWatchdog(idleMs: number): { signal: AbortSignal; touch: () => void; stop: () => void } {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const touch = () => {
    clearTimeout(timer);
    timer = setTimeout(() => controller.abort(), idleMs);
  };
  touch();
  return { signal: controller.signal, touch, stop: () => clearTimeout(timer) };
}

export function createApi(fetchFn: FetchFn, options: ApiOptions = {}): Api {
  const idleMs = options.idleMs ?? STREAM_IDLE_MS;

  async function call<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
    let response: Response;
    try {
      response = await fetchFn(path, init);
    } catch {
      return { ok: false, status: 0, error: 'network', body: null };
    }
    const body = await jsonBody(response);
    if (response.ok) return { ok: true, status: response.status, data: body as T };
    return { ok: false, status: response.status, error: classifyError(response.status, body), body };
  }

  async function stream(path: string, init: RequestInit, onEvent: (event: SseEvent) => void): Promise<StreamEnd> {
    const watch = idleWatchdog(idleMs);
    try {
      let response: Response;
      try {
        response = await fetchFn(path, {
          ...init, headers: { ...(init.headers ?? {}), accept: 'text/event-stream' }, signal: watch.signal,
        });
      } catch {
        return { type: 'broken' };
      }
      if (!isStream(response)) {
        const body = await jsonBody(response);
        return { type: 'error', error: classifyError(response.ok ? 500 : response.status, body), body };
      }
      try {
        await readSse(response.body!, onEvent, watch.touch);
        return { type: 'ended' };
      } catch {
        return { type: 'broken' };
      }
    } finally {
      watch.stop();
    }
  }

  return {
    async createReading(body) {
      const result = await call<Record<string, unknown>>('/api/readings', {
        method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body),
      });
      if (!result.ok) return { type: 'error', error: result.error, body: result.body };
      if (result.data?.group === 'crisis') return { type: 'crisis', payload: result.data as unknown as CrisisPayload };
      return { type: 'reading', reading: result.data as unknown as ReadingCreated };
    },
    streamReading(id, tz, onEvent) {
      return stream(withQuery(readingPath(id, '/stream'), { tz }), { method: 'GET' }, onEvent);
    },
    retryReading(id, tz, onEvent) {
      return stream(withQuery(readingPath(id, '/retry'), { tz }), { method: 'POST' }, onEvent);
    },
    getReading(id, tz) {
      return call<ReadingView>(withQuery(readingPath(id), { tz }));
    },
    async postFollowup(id, body, onEvent) {
      // The API sends headers only after its question check, so a request that breaks here may already have
      // stored (and charged) the follow-up: report it as a broken stream and let the caller restore from GET.
      const watch = idleWatchdog(idleMs);
      try {
        let response: Response;
        try {
          response = await fetchFn(readingPath(id, '/followups'), {
            method: 'POST', headers: { ...JSON_HEADERS, accept: 'text/event-stream' }, body: JSON.stringify(body),
            signal: watch.signal,
          });
        } catch {
          return { type: 'stream', end: { type: 'broken' } };
        }
        if (!isStream(response)) return { type: 'refused', refusal: followupRefusal(response.status, await jsonBody(response)) };
        try {
          await readSse(response.body!, onEvent, watch.touch);
          return { type: 'stream', end: { type: 'ended' } };
        } catch {
          return { type: 'stream', end: { type: 'broken' } };
        }
      } finally {
        watch.stop();
      }
    },
    getDaily(lang, tz) {
      return call<DailyCard>(withQuery('/api/daily', { lang, tz }));
    },
    joinWaitlist(email, lang) {
      return call<{ ok: boolean }>('/api/plus/waitlist', {
        method: 'POST', headers: JSON_HEADERS, body: JSON.stringify({ email, lang }),
      });
    },
  };
}

/** The browser's fetch, called with the right `this`. */
export function browserFetch(): FetchFn {
  return (input, init) => fetch(input, init);
}
