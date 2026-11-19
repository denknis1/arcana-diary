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

function bytes(text: string): Uint8Array {
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

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(body === null ? null : JSON.stringify(body), {
    status, headers: { 'content-type': 'application/json' },
  });
}

/** Answers calls in order; an Error in the queue is thrown (no network). */
export function fakeFetch(...queue: Array<Response | Error>): { fetch: FetchFn; calls: Call[] } {
  const calls: Call[] = [];
  const fetchFn: FetchFn = async (url, init) => {
    const headers = (init?.headers ?? {}) as Record<string, string>;
    calls.push({ url, method: init?.method ?? 'GET', body: init?.body ? JSON.parse(String(init.body)) : undefined, headers });
    const next = queue.shift();
    if (!next) throw new Error(`unexpected call ${url}`);
    if (next instanceof Error) throw next;
    return next;
  };
  return { fetch: fetchFn, calls };
}
