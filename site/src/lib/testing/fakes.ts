// Test doubles for the API: Responses as the API sends them, and a fetch that answers from a queue.
import type { FetchFn } from '../api';

export interface Call {
  url: string;
  method: string;
  body: unknown;
  headers: Record<string, string>;
}

export function sseText(events: ReadonlyArray<readonly [string, unknown]>): string {
  return events.map(([name, data]) => `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`).join('');
}

function bytes(text: string): Uint8Array<ArrayBuffer> {
  return new TextEncoder().encode(text);
}

export function sseResponse(text: string): Response {
  return new Response(bytes(text), { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

/** A stream that sends `text` and then breaks (the phone lost its connection). */
export function brokenSseResponse(text: string): Response {
  let pulls = 0;
  const body = new ReadableStream<Uint8Array>({
    pull(controller) {
      pulls += 1;
      if (pulls === 1) controller.enqueue(bytes(text));
      else controller.error(new TypeError('network error'));
    },
  });
  return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } });
}

const stalls = new WeakMap<Response, ReadableStreamDefaultController<Uint8Array>>();

/** A stream that sends `text` and then goes silent for good (half-open connection); aborting the request ends it. */
export function stalledSseResponse(text = ''): Response {
  let control!: ReadableStreamDefaultController<Uint8Array>;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      control = controller;
      if (text) controller.enqueue(bytes(text));
    },
  });
  const response = new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } });
  stalls.set(response, control);
  return response;
}

/** A stream that sends each piece `everyMs` apart, then ends; aborting the request breaks it. */
export function slowSseResponse(pieces: string[], everyMs: number): Response {
  let index = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let control!: ReadableStreamDefaultController<Uint8Array>;
  const next = () => {
    timer = setTimeout(() => {
      if (index < pieces.length) {
        control.enqueue(bytes(pieces[index++]));
        next();
      } else control.close();
    }, everyMs);
  };
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      control = controller;
      next();
    },
    cancel() {
      clearTimeout(timer);
    },
  });
  const response = new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } });
  stalls.set(response, { error: (e: unknown) => { clearTimeout(timer); control.error(e); } } as ReadableStreamDefaultController<Uint8Array>);
  return response;
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

/** Answers calls in order; an Error in the queue is thrown (no network). */
export function fakeFetch(...queue: Array<Response | Error>): { fetch: FetchFn; calls: Call[]; signals: Array<AbortSignal | undefined> } {
  const calls: Call[] = [];
  const signals: Array<AbortSignal | undefined> = [];
  const fetchFn: FetchFn = async (url, init) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    signals.push(init?.signal ?? undefined);
    calls.push({ url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : undefined, headers });
    const next = queue.shift();
    if (!next) throw new Error(`unexpected call ${url}`);
    if (next instanceof Error) throw next;
    const stall = stalls.get(next);
    if (stall && init?.signal) {
      const abort = () => stall.error(new DOMException('aborted', 'AbortError'));
      if (init.signal.aborted) abort();
      else init.signal.addEventListener('abort', abort, { once: true });
    }
    return next;
  };
  return { fetch: fetchFn, calls, signals };
}

/** Answers by "METHOD /path?query" or, failing that, "METHOD /path"; anything else throws (no network). For screens
 * that make several requests at once (the diary: settings, claim, list). */
export function routeFetch(routes: Record<string, (call: Call) => Response>): { fetch: FetchFn; calls: Call[] } {
  const calls: Call[] = [];
  const fetchFn: FetchFn = async (url, init) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    const call: Call = { url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : undefined, headers };
    calls.push(call);
    const route = routes[`${call.method} ${url}`] ?? routes[`${call.method} ${url.split('?')[0]}`];
    if (!route) throw new Error(`unexpected call ${call.method} ${url}`);
    return route(call);
  };
  return { fetch: fetchFn, calls };
}
