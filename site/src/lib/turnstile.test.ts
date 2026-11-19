import { beforeEach, describe, expect, it } from 'vitest';
import { TURNSTILE_SRC, loadTurnstile, resetTurnstileForTests, turnstileToken, type TurnstileApi, type TurnstileHost } from './turnstile';

interface FakeEl { tagName: string; src?: string; async?: boolean; className?: string; onload?: () => void; onerror?: () => void; removed?: boolean; remove(): void }

function fakeHost(behaviour: 'token' | 'error' | 'silent' | 'noscript') {
  const appended: FakeEl[] = [];
  const timers: Array<() => void> = [];
  const api: TurnstileApi & { rendered: Record<string, unknown>[]; removed: string[] } = {
    rendered: [], removed: [],
    render(_el, options) {
      this.rendered.push(options);
      if (behaviour === 'token') (options.callback as (t: string) => void)('tok-1');
      if (behaviour === 'error') (options['error-callback'] as () => void)();
      return 'w1';
    },
    remove(id) { this.removed.push(id); },
  };
  const host = {
    document: {
      createElement: (tag: string) => ({ tagName: tag, remove() { this.removed = true; } }) as FakeEl,
      querySelector: () => null,
      head: { appendChild: (el: FakeEl) => { appended.push(el); if (behaviour === 'noscript') el.onerror!(); else { (host.window as { turnstile?: TurnstileApi }).turnstile = api; el.onload!(); } } },
      body: { appendChild: (el: FakeEl) => { appended.push(el); } },
    },
    window: {
      turnstile: undefined as TurnstileApi | undefined,
      setTimeout: ((fn: () => void) => { timers.push(fn); return 1; }) as unknown as typeof setTimeout,
      clearTimeout: (() => {}) as typeof clearTimeout,
    },
  };
  return { host: host as unknown as TurnstileHost, appended, api, timers };
}

beforeEach(() => resetTurnstileForTests());

describe('turnstile', () => {
  it('loads the script only when asked, once', async () => {
    const { host, appended } = fakeHost('token');
    expect(appended).toHaveLength(0);
    const [a, b] = await Promise.all([loadTurnstile(host), loadTurnstile(host)]);
    expect(a).toBe(b);
    const scripts = appended.filter((el) => el.tagName === 'script');
    expect(scripts).toHaveLength(1);
    expect(scripts[0].src).toBe(TURNSTILE_SRC);
  });

  it('gets a token from the invisible widget with the API’s site key and cleans up', async () => {
    const { host, api, appended } = fakeHost('token');
    expect(await turnstileToken('0xSITE', host)).toBe('tok-1');
    expect(api.rendered[0].sitekey).toBe('0xSITE');
    expect(appended.find((el) => el.className === 'turnstile-slot')!.removed).toBe(true);
  });

  it('gives null when the check fails, times out or the script is blocked', async () => {
    expect(await turnstileToken('k', fakeHost('error').host)).toBeNull();
    const silent = fakeHost('silent');
    const pending = turnstileToken('k', silent.host);
    while (silent.timers.length === 0) await new Promise((r) => setTimeout(r, 0));
    silent.timers.forEach((fire) => fire());
    expect(await pending).toBeNull();
    resetTurnstileForTests();
    expect(await turnstileToken('k', fakeHost('noscript').host)).toBeNull();
  });
});

describe('turnstile token flow', () => {
  it('removes the widget when the callback fires inside render, and counts only the first outcome', async () => {
    const f = fakeHost('token');
    const orig = f.api.render.bind(f.api);
    f.api.render = (el, o) => { const id = orig(el, o); (o['error-callback'] as () => void)(); return id; };
    expect(await turnstileToken('k', f.host)).toBe('tok-1');
    expect(f.api.removed).toEqual(['w1']);
  });

  it('lets a later attempt load again when onload fires without window.turnstile', async () => {
    const appended: FakeEl[] = [];
    const host = {
      document: { createElement: () => ({ remove() {} }) as FakeEl, querySelector: () => null, body: { appendChild() {} },
        head: { appendChild: (el: FakeEl) => { appended.push(el); el.onload!(); } } },
      window: { turnstile: undefined, setTimeout, clearTimeout },
    } as unknown as TurnstileHost;
    await expect(loadTurnstile(host)).rejects.toThrow();
    await expect(loadTurnstile(host)).rejects.toThrow();
    expect(appended).toHaveLength(2);
  });
});
