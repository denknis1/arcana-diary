// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../lib/analytics';
import { forgetAuth } from '../lib/auth';
import { forgetAuthConfig } from '../lib/authConfig';
import { SIGNED_IN_KEY, STARTED_KEY } from '../lib/authState';
import { byText, cleanup, click, mount, queryText, settle, submit, typeInto, waitFor } from '../lib/testing/dom';
import { jsonResponse, routeFetch, type Call } from '../lib/testing/fakes';
import DiaryIsland from './DiaryIsland';

type FakeSession = { access_token: string; user?: { email?: string; app_metadata?: { provider?: string } } };
const h = vi.hoisted(() => ({ session: null as FakeSession | null, error: null as unknown, sent: [] as unknown[], loadFails: 0 }));
vi.mock('../lib/supabaseClient', () => ({ // the sign-in library is never loaded in tests
  createClient: () => {
    if (h.loadFails > 0) { // the library's chunk did not arrive (offline for a moment)
      h.loadFails -= 1;
      throw new Error('chunk failed');
    }
    return {
      getSession: async () => ({ data: { session: h.session }, error: h.error }),
      refreshSession: async () => ({ data: { session: null }, error: null }),
      signInWithOtp: async (args: unknown) => { h.sent.push(args); return { error: null }; },
      signInWithOAuth: async () => ({ error: null }),
      signOut: async () => { h.session = null; return { error: null }; },
    };
  },
}));
vi.mock('../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../lib/analytics')>()), sendEvent: vi.fn(),
}));

const ON = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: false };
// created_at from a local date: the list shows the local day, so the test holds in any time zone
const ITEM = {
  id: '2b3c4d5e-0000-4000-8000-000000000001', created_at: new Date(2026, 10, 20, 12).toISOString(), lang: 'en', kind: 'three',
  topic: 'work', question: 'Will the <b>move</b> go well?', headline: 'Slow and steady.', answer_shown: 'model',
  cards: [{ card_id: 'major-18-moon', position: 'past', reversed: true, name: 'The Moon' }], outcome: 'partly',
  has_note: true, followups: 1,
};
const CRISIS = { ...ITEM, id: '2b3c4d5e-0000-4000-8000-000000000002', question: null, topic: null, headline: null,
  answer_shown: 'crisis', outcome: null, has_note: false };
const page = (items: unknown[], hidden = 0) => () => jsonResponse(200, { items, next_before: null, hidden_count: hidden });

function serve(routes: Record<string, (call: Call) => Response>) {
  const served = routeFetch({ 'GET /api/auth-config': () => jsonResponse(200, ON), ...routes });
  vi.stubGlobal('fetch', served.fetch);
  return served;
}

/** Mounts the page and waits until `ready` passes: the settings, the library (mocked), the claim and the list come
 * one after another (waitFor, not a count of rounds — review I11). */
async function open(ready: (root: HTMLElement) => unknown) {
  const mounted = await mount(<DiaryIsland lang="en" />);
  await waitFor(() => ready(mounted.root));
  return mounted;
}

beforeEach(() => history.replaceState(null, '', '/diary'));
afterEach(() => {
  cleanup();
  localStorage.clear();
  forgetAuthConfig();
  forgetAuth();
  h.session = null;
  h.error = null;
  h.sent = [];
  h.loadFails = 0;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.mocked(sendEvent).mockClear();
});

describe('the diary page (screen 4a; spec 4.4b §5)', () => {
  it('says that signing in opens soon when sign-in is off', async () => {
    serve({ 'GET /api/auth-config': () => jsonResponse(200, { enabled: false, supabase_url: '', anon_key: '', google: false }) });
    await open((root) => byText(root, 'Signing in opens soon.'));
  });

  it('a page restored from the back/forward cache reloads, and the listener goes with the page (review M5)', async () => {
    serve({});
    const reload = vi.spyOn(location, 'reload').mockImplementation(() => {});
    const { unmount } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    const restored = (persisted: boolean) => {
      const event = new Event('pageshow');
      Object.defineProperty(event, 'persisted', { value: persisted });
      window.dispatchEvent(event);
    };
    restored(false);
    expect(reload).not.toHaveBeenCalled();
    restored(true);
    expect(reload).toHaveBeenCalledTimes(1);
    unmount();
    restored(true);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it('not signed in: one line why and the sign-in block, and no claim', async () => {
    const served = serve({});
    const { root } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    expect(root.textContent).toContain('Save your readings here and come back to see what came true.');
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/auth-config']);
  });

  it('after the e-mail link on another device: claims only the token once, gives consent, counts signup_done and cleans the address', async () => {
    // the session came in the address: the library's session is the one of #access_token, so this page load
    // finished the sign-in (owner decision 15; final review I1)
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1#access_token=tok-a');
    h.session = { access_token: 'tok-a', user: { app_metadata: { provider: 'email' } } };
    const served = serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'PATCH /api/account': () => jsonResponse(200, { email: 'ana@example.com', reminders_consent: true, consent_at: null }),
      'GET /api/diary': page([ITEM]),
    });
    await open(() => expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual([
      'GET /api/auth-config', 'POST /api/account/claim', 'PATCH /api/account', 'GET /api/diary?limit=10']));
    expect(served.calls[1].body).toEqual({ tokens: ['tok-1'], device: false }); // no mark here: owner decision 12
    expect(served.calls[1].headers.authorization).toBe('Bearer tok-a');
    expect(served.calls[2].body).toEqual({ reminders_consent: true });
    expect(`${location.pathname}${location.search}`).toBe('/diary');
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'signup_done', tool: null, lang: 'en', params: { method: 'email' } });
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1');
  });

  it('a reminder switched on by the sign-in says so, with the account page to turn it off (owner decision 16)', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1#access_token=tok-a');
    h.session = { access_token: 'tok-a', user: { app_metadata: { provider: 'email' } } };
    serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'PATCH /api/account': () => jsonResponse(200, { email: 'ana@example.com', reminders_consent: true, consent_at: null }),
      'GET /api/diary': page([ITEM]),
    });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(1));
    const line = root.querySelector('p[role="status"]');
    expect(line?.textContent).toBe('The reminder in 7 days is on — you can turn it off in your account.');
    const link = line?.querySelector('a');
    expect(link?.textContent).toBe('your account');
    expect(link?.getAttribute('href')).toBe('/account');
    expect(queryText(root, 'The reminder was not switched on. You can switch it on in your account.')).toBeNull();
  });

  it('the reminder line in Spanish links to the Spanish account page (owner decision 16)', async () => {
    history.replaceState(null, '', '/es/diario?claim=tok-1&remind=1#access_token=tok-a');
    h.session = { access_token: 'tok-a', user: { app_metadata: { provider: 'email' } } };
    serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'PATCH /api/account': () => jsonResponse(200, { email: 'ana@example.com', reminders_consent: true, consent_at: null }),
      'GET /api/diary': page([ITEM]),
    });
    const mounted = await mount(<DiaryIsland lang="es" />);
    await waitFor(() => expect(mounted.root.querySelectorAll('a.diary-item')).toHaveLength(1));
    const line = mounted.root.querySelector('p[role="status"]');
    expect(line?.textContent).toBe('El recordatorio en 7 días está activado — puedes desactivarlo en tu cuenta.');
    expect(line?.querySelector('a')?.textContent).toBe('tu cuenta');
    expect(line?.querySelector('a')?.getAttribute('href')).toBe('/es/cuenta');
  });

  it('a sign-in that switched no reminder on shows no reminder line (consent "none")', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1#access_token=tok-a');
    h.session = { access_token: 'tok-a', user: { app_metadata: { provider: 'email' } } };
    serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'GET /api/diary': page([ITEM]),
    });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(root.querySelector('p[role="status"]')).toBeNull();
    expect(root.textContent).not.toContain('The reminder');
  });

  it('a forged #access_token on someone else\'s link opened while signed in: nothing claimed, no consent, no event, address cleaned (final review I1)', async () => {
    // the library keeps the existing session when the address login fails (GoTrueClient.js:406-421): the session is
    // not the one of the hash, so this page load finished no sign-in (owner decision 15)
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1#access_token=x');
    h.session = { access_token: 'tok-a', user: { app_metadata: { provider: 'email' } } };
    const served = serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'PATCH /api/account': () => jsonResponse(200, { email: 'ana@example.com', reminders_consent: true, consent_at: null }),
      'GET /api/diary': page([ITEM]),
    });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/auth-config', 'GET /api/diary?limit=10']);
    expect(vi.mocked(sendEvent)).not.toHaveBeenCalledWith(expect.objectContaining({ name: 'signup_done' }));
    expect(`${location.pathname}${location.search}${location.hash}`).toBe('/diary');
    expect(root.textContent).not.toContain('The reminder');
  });

  it('an ordinary visit claims nothing and lists the entries as text, a crisis entry without text', async () => {
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': page([ITEM, CRISIS]) });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(2));
    expect(served.calls.some((c) => c.url === '/api/account/claim')).toBe(false);
    const links = Array.from(root.querySelectorAll<HTMLAnchorElement>('a.diary-item'));
    expect(links.map((a) => a.getAttribute('href'))).toEqual([`/diary?r=${ITEM.id}`, `/diary?r=${CRISIS.id}`]);
    expect(links[0].textContent).toContain('Will the <b>move</b> go well?'); // text, never markup
    expect(root.querySelector('a.diary-item b')).toBeNull();
    expect(links[0].textContent).toContain('20 November 2026 · Three cards');
    expect(links[0].textContent).toContain('Slow and steady.');
    expect(links[0].textContent).toContain('Partly');
    expect(links[0].textContent).toContain('Has a note');
    expect(links[1].querySelector('.diary-item__question')).toBeNull();
    expect(links[1].querySelector('.diary-item__headline')).toBeNull();
  });

  it('more than ten: the hidden line and the Plus card with the whole-diary benefit', async () => {
    h.session = { access_token: 'tok-a' };
    serve({ 'GET /api/diary': page([ITEM], 3) });
    const { root } = await open((r) => byText(r, 'More readings in Plus: 3'));
    expect(byText(root, 'What Plus gives you')).toBeTruthy();
    expect(byText(root, 'Your whole diary, with no limit')).toBeTruthy();
    expect(byText(root, 'Your diary keeps your last 10 readings. Plus keeps all of them.')).toBeTruthy();
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'plus_view', tool: null, lang: 'en', params: { place: 'diary' } });
  });

  it('an empty diary offers a reading', async () => {
    h.session = { access_token: 'tok-a' };
    serve({ 'GET /api/diary': page([]) });
    const { root } = await open((r) => byText(r, 'Your saved readings will appear here.'));
    expect(byText<HTMLAnchorElement>(root, 'Get a free reading', 'a').getAttribute('href')).toBe('/');
  });

  it('a 401 without JSON (the stage cookie) is the stage line with a reload button — one request, no loop (review I2)', async () => {
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': () => new Response('', { status: 401 }) });
    const { root } = await open((r) => byText(r, 'Your session on this preview site has expired. Reload the page to continue.'));
    await settle();
    expect(served.calls.filter((c) => c.url.startsWith('/api/diary'))).toHaveLength(1);
    expect(byText(root, 'Try again', 'button')).toBeTruthy(); // it reloads the page (spec §3)
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1'); // not signed out: the token was never refused
  });

  it('a list that could not be read says so and "Try again" asks once more (review M18)', async () => {
    h.session = { access_token: 'tok-a' };
    let lists = 0;
    serve({ 'GET /api/diary': () => (lists++ === 0 ? jsonResponse(503, { reason: 'db' }) : page([ITEM])()) });
    const { root } = await open((r) => byText(r, 'The service is unavailable right now. Please try again in a few minutes.'));
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => expect(root.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(lists).toBe(2);
  });

  it('a library error with no session: the try-again view, the sign-in kept; "Try again" opens the diary (controller, Task 14 review)', async () => {
    localStorage.setItem(SIGNED_IN_KEY, '1');
    h.error = { message: 'Failed to fetch' }; // the library answered with an error and no session: not "signed out"
    const served = serve({ 'GET /api/diary': page([ITEM]) });
    const { root } = await open((r) => byText(r, 'The service is unavailable right now. Please try again in a few minutes.'));
    expect(root.querySelector('input[type="email"]')).toBeNull();
    expect(root.querySelector('.help-line')).not.toBeNull();
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1');
    h.error = null;
    h.session = { access_token: 'tok-a' };
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => expect(root.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(served.calls.filter((c) => c.url.startsWith('/api/diary'))).toHaveLength(1);
  });

  it('a clean "no session": the sign-in block, the flag cleared, so sending the link marks "started here" (handoff 6)', async () => {
    localStorage.setItem(SIGNED_IN_KEY, '1'); // left from a session that went (signed out in another tab, say)
    serve({});
    const { root } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBeNull();
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await waitFor(() => byText(root, 'Check your e-mail'));
    expect(JSON.parse(localStorage.getItem(STARTED_KEY) ?? 'null')).toMatchObject({ method: 'email' });
    expect(h.sent).toEqual([{ email: 'ana@example.com',
      options: { emailRedirectTo: 'https://arcana.test/diary', shouldCreateUser: true } }]);
  });

  it('a library that did not load: the try-again view, the sign-in kept; a later open works', async () => {
    localStorage.setItem(SIGNED_IN_KEY, '1');
    h.session = { access_token: 'tok-a' };
    h.loadFails = 1;
    serve({ 'GET /api/diary': page([ITEM]) });
    const { root } = await open((r) => byText(r, 'The service is unavailable right now. Please try again in a few minutes.'));
    expect(root.querySelector('input[type="email"]')).toBeNull();
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1');
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => expect(root.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBe('1');
  });

  it('a claim refused by the stage cookie: the stage line without the help line, and "Try again" reloads the page', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1#access_token=tok-a');
    h.session = { access_token: 'tok-a' };
    const reload = vi.spyOn(location, 'reload').mockImplementation(() => {});
    const served = serve({ 'POST /api/account/claim': () => new Response('', { status: 401 }) });
    const { root } = await open((r) => byText(r, 'Your session on this preview site has expired. Reload the page to continue.'));
    expect(root.querySelector('.help-line')).toBeNull();
    await click(byText(root, 'Try again', 'button'));
    await settle();
    expect(reload).toHaveBeenCalledTimes(1);
    expect(served.calls.filter((c) => c.url === '/api/account/claim')).toHaveLength(1); // not claimed again
  });

  it('an expired e-mail link: the line about it above the sign-in block', async () => {
    history.replaceState(null, '', '/diary#error=access_denied&error_code=otp_expired');
    serve({});
    const { root } = await open((r) => byText(r, 'This link has expired or was already used. Send yourself a new one below.'));
    expect(root.querySelector('input[type="email"]')).not.toBeNull();
  });

  it('an expired e-mail link: once the line is shown the hash leaves the address, the query stays (final review M3)', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1#error=access_denied&error_code=otp_expired');
    serve({});
    const { root } = await open((r) => byText(r, 'This link has expired or was already used. Send yourself a new one below.'));
    expect(location.hash).toBe('');
    expect(`${location.pathname}${location.search}`).toBe('/diary?claim=tok-1&remind=1'); // the sign-in here keeps them
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await waitFor(() => expect(h.sent).toHaveLength(1));
    expect(h.sent[0]).toMatchObject({ options: { emailRedirectTo: 'https://arcana.test/diary?claim=tok-1&remind=1' } });
  });

  it('someone else\'s link opened while signed in (no session in the address, no mark): nothing claimed, address cleaned (owner decision 15)', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1');
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': page([ITEM]) });
    await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/auth-config', 'GET /api/diary?limit=10']);
    expect(`${location.pathname}${location.search}`).toBe('/diary');
    expect(vi.mocked(sendEvent)).not.toHaveBeenCalledWith(expect.objectContaining({ name: 'signup_done' }));
  });

  it('a claim that failed: "Try again" claims the same token (still this page load\'s sign-in)', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1#access_token=tok-a');
    h.session = { access_token: 'tok-a' };
    let claims = 0;
    const served = serve({
      'POST /api/account/claim': () => (claims++ === 0 ? jsonResponse(503, { reason: 'db' }) : jsonResponse(200, { claimed: [ITEM.id] })),
      'GET /api/diary': page([ITEM]),
    });
    const { root } = await open((r) => byText(r, 'The service is unavailable right now. Please try again in a few minutes.'));
    expect(root.querySelector('.help-line')).not.toBeNull(); // a 503 links to the help lines (needsHelpLink)
    expect(location.search).toBe('?claim=tok-1'); // nothing changed yet: the address keeps its token
    await click(byText(root, 'Try again', 'button'));
    await waitFor(() => expect(root.querySelectorAll('a.diary-item')).toHaveLength(1));
    const claimCalls = served.calls.filter((c) => c.url === '/api/account/claim');
    expect(claimCalls.map((c) => c.body)).toEqual([{ tokens: ['tok-1'], device: false }, { tokens: ['tok-1'], device: false }]);
    expect(location.search).toBe('');
  });

  it('the reminder asked for but not saved: one line, and the list', async () => {
    history.replaceState(null, '', '/diary?claim=tok-1&remind=1#access_token=tok-a');
    h.session = { access_token: 'tok-a' };
    serve({
      'POST /api/account/claim': () => jsonResponse(200, { claimed: [ITEM.id] }),
      'PATCH /api/account': () => jsonResponse(503, { reason: 'db' }),
      'GET /api/diary': page([ITEM]),
    });
    const { root } = await open((r) => expect(r.querySelectorAll('a.diary-item')).toHaveLength(1));
    expect(byText(root, 'The reminder was not switched on. You can switch it on in your account.')).toBeTruthy();
    expect(root.textContent).not.toContain('The reminder in 7 days is on'); // owner decision 16: only on 'set'
  });

  it('a 401 "sign_in" signs out on this device and opens the page again: the session gone — the sign-in block', async () => {
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': () => { h.session = null; return jsonResponse(401, { reason: 'sign_in' }); } });
    const { root } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    expect(root.textContent).toContain('Save your readings here and come back to see what came true.');
    expect(served.calls.filter((c) => c.url.startsWith('/api/diary'))).toHaveLength(1);
    expect(localStorage.getItem(SIGNED_IN_KEY)).toBeNull();
  });

  it('a second 401 "sign_in" on the same page shows "Try again" — never a loop of requests (review I2)', async () => {
    h.session = { access_token: 'tok-a' };
    const served = serve({ 'GET /api/diary': () => jsonResponse(401, { reason: 'sign_in' }) });
    const { root } = await open((r) => byText(r, 'Try again', 'button'));
    await settle();
    expect(served.calls.filter((c) => c.url.startsWith('/api/diary'))).toHaveLength(2);
    expect(byText(root, 'Something went wrong. Please try again.')).toBeTruthy();
    expect(queryText(root, 'Save your readings here and come back to see what came true.')).toBeNull();
  });

  it('?r=<id> opens that entry of the account (screen 4b)', async () => {
    history.replaceState(null, '', `/diary?r=${ITEM.id}`);
    h.session = { access_token: 'tok-a' };
    serve({ [`GET /api/readings/${ITEM.id}`]: () => jsonResponse(200, {
      id: ITEM.id, kind: 'three', topic: 'work', question: 'Will the move go well?', created_at: ITEM.created_at,
      cards: ITEM.cards, verdict: null, soft_line: null, answer_shown: 'model', status: 'done', retries_left: 0,
      answer: { headline: 'Slow and steady.' }, followups: [], followups_left: 2, followup_attempts_left: 8,
      in_diary: true, outcome: null, note: null,
    }) });
    const { root } = await open((r) => expect(r.querySelector('h2')?.textContent).toBe('Will the move go well?'));
    expect(byText<HTMLAnchorElement>(root, '← Your diary', 'a').getAttribute('href')).toBe('/diary');
  });

  it('signing in from an entry\'s address comes back to that entry (review M21)', async () => {
    history.replaceState(null, '', `/diary?r=${ITEM.id}`);
    serve({});
    const { root } = await open((r) => expect(r.querySelector('input[type="email"]')).not.toBeNull());
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await waitFor(() => expect(h.sent).toHaveLength(1));
    expect(h.sent[0]).toMatchObject({ options: { emailRedirectTo: `https://arcana.test/diary?r=${ITEM.id}` } });
  });
});
