// Our own event counter (spec 4.4a §6, docs/design/analytics-events.md): POST /api/events with
// {"name", "tool", "lang", "params"} by navigator.sendBeacon, else fetch with keepalive. No cookie, no id, no
// question text; a failure never reaches the reading.
import type { Lang, Tool } from './types';

export type EventName = 'tool_view' | 'draw_click' | 'night_open' | 'cards_revealed' | 'reading_shown'
  | 'more_about_cards' | 'plus_view' | 'save_click' | 'signup_done' | 'outcome_answered' | 'remind_click';

/** The events of docs/design/analytics-events.md that carry no tool. */
export const NO_TOOL: ReadonlySet<EventName> = new Set<EventName>(['plus_view', 'signup_done', 'outcome_answered']);

export type Params = Record<string, string | number | boolean>;

export interface AnalyticsEvent {
  name: EventName;
  tool: Tool | null;
  lang: Lang;
  params: Params;
}

export const EVENTS_URL = '/api/events';

/** plus_view, signup_done and outcome_answered carry no tool; every other event names its tool. */
export function analyticsEvent(name: EventName, tool: Tool | null, lang: Lang, params: Params = {}): AnalyticsEvent {
  const clean: Params = { ...params };
  if ('ms_from_draw' in clean) {
    const ms = Number(clean.ms_from_draw);
    clean.ms_from_draw = Number.isFinite(ms) ? Math.min(600000, Math.max(0, Math.round(ms))) : 0;
  }
  return { name, tool: NO_TOOL.has(name) ? null : tool, lang, params: clean };
}

export interface Transport {
  sendBeacon?: (url: string, data: Blob) => boolean;
  fetch?: (url: string, init: RequestInit) => Promise<unknown>;
}

export function browserTransport(): Transport {
  const nav = typeof navigator === 'undefined' ? undefined : navigator;
  return {
    sendBeacon: nav && typeof nav.sendBeacon === 'function' ? (url, data) => nav.sendBeacon(url, data) : undefined,
    fetch: typeof fetch === 'function' ? (url, init) => fetch(url, init) : undefined,
  };
}

export function sendEvent(event: AnalyticsEvent, transport: Transport = browserTransport()): void {
  const body = JSON.stringify(event);
  try {
    if (transport.sendBeacon?.(EVENTS_URL, new Blob([body], { type: 'application/json' }))) return;
  } catch {
    // fall through to fetch
  }
  try {
    transport.fetch?.(EVENTS_URL, {
      method: 'POST', body, headers: { 'content-type': 'application/json' }, keepalive: true, credentials: 'same-origin',
    })?.catch(() => {});
  } catch {
    // the counter never breaks the page
  }
}
