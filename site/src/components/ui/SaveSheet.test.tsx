// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAccountApi, type AccountApi } from '../../lib/accountApi';
import { CREATE_TIMEOUT_MS, type FetchFn } from '../../lib/api';
import type { Auth, SendResult } from '../../lib/auth';
import { SIGNED_IN_KEY, STARTED_KEY } from '../../lib/authState';
import { byText, cleanup, click, mount, queryText, settle, submit, typeInto } from '../../lib/testing/dom';
import { SaveSheet } from './SaveSheet';
import { RESEND_WAIT_S } from './SignInBlock';

function fakes(token: string | null = 'tok-1', answers: SendResult[] = [], claim?: AccountApi['claimToken']) {
  const sent: Array<{ method: 'email' | 'google'; email?: string; redirectTo: string }> = [];
  const tokens: string[] = [];
  const auth: Pick<Auth, 'sendLink' | 'google'> = {
    sendLink: async (email, redirectTo) => { sent.push({ method: 'email', email, redirectTo }); return answers.shift() ?? { ok: true }; },
    google: async (redirectTo) => { sent.push({ method: 'google', redirectTo }); return { ok: true }; },
  };
  const accountApi: Pick<AccountApi, 'claimToken'> = {
    claimToken: claim ?? (async (id) => {
      tokens.push(id);
      return token ? { ok: true, status: 201, data: { token, expires_at: '2026-11-29T00:00:00Z' } }
        : { ok: false, status: 409, error: 'other', body: { reason: 'in_diary' } };
    }),
  };
  return { auth, accountApi, sent, tokens };
}

function sheet(f: ReturnType<typeof fakes>, props: { lang?: 'en' | 'es'; google?: boolean; onClose?: () => void } = {}) {
  return (
    <SaveSheet lang={props.lang ?? 'en'} readingId="r1" auth={f.auth} google={props.google ?? false}
      accountApi={f.accountApi} origin="https://arcana.test" onClose={props.onClose ?? (() => {})} />
  );
}

afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.useRealTimers();
});

describe('the save sheet (screens 3, 3b; spec 4.4b §4)', () => {
  it('sends the e-mail link back to the diary with the claim token and the reminder, then shows "Check your e-mail"', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f));
    expect(document.activeElement?.textContent).toBe('Save to your diary');
    const remind = root.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    expect(remind.checked).toBe(false); // off unless ticked (design review В3)
    await click(remind);
    await typeInto(root.querySelector('input[type="email"]')!, ' ana@example.com ');
    await submit(root.querySelector('form')!);
    expect(f.tokens).toEqual(['r1']);
    expect(f.sent).toEqual([{ method: 'email', email: 'ana@example.com', redirectTo: 'https://arcana.test/diary?claim=tok-1&remind=1' }]);
    expect(JSON.parse(localStorage.getItem(STARTED_KEY)!).method).toBe('email');
    expect(document.activeElement?.textContent).toBe('Check your e-mail');
    expect(root.textContent).toContain('We sent a link to ana@example.com.');
    expect(queryText(root, 'Continue with Google')).toBeNull(); // Google is off
  });

  it('without a claim token (already saved, too many) still returns to the diary of the page language', async () => {
    const f = fakes(null);
    const { root } = await mount(sheet(f, { lang: 'es' }));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(f.sent[0].redirectTo).toBe('https://arcana.test/es/diario');
    expect(byText(root, 'Revisa tu correo')).toBeTruthy();
  });

  it('offers Google when it is on and marks the sign-in as started here', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f, { google: true }));
    await click(byText(root, 'Continue with Google', 'button'));
    expect(f.sent).toEqual([{ method: 'google', redirectTo: 'https://arcana.test/diary?claim=tok-1' }]);
    expect(JSON.parse(localStorage.getItem(STARTED_KEY)!).method).toBe('google');
  });

  it('says what went wrong: a wrong e-mail before sending, "too often" from Supabase', async () => {
    const f = fakes('tok-1', [{ ok: false, error: 'tooOften' }]);
    const { root } = await mount(sheet(f));
    const email = root.querySelector('input[type="email"]')!;
    await typeInto(email, 'not-an-email');
    await submit(root.querySelector('form')!);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe('Please check the e-mail address and try again.');
    expect(f.sent).toEqual([]);
    await typeInto(email, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe('Too many tries for now. Please wait a few minutes and try again.');
    expect(root.querySelector('input[type="email"]')).not.toBeNull(); // still the form
  });

  it('lets the link be sent again only after 60 seconds, with the same token', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const f = fakes();
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(byText<HTMLButtonElement>(root, 'Send it again', 'button').disabled).toBe(true);
    expect(root.textContent).toContain(`You can send it again in ${RESEND_WAIT_S} s.`);
    await act(() => {
      vi.advanceTimersByTime(RESEND_WAIT_S * 1000);
    });
    expect(byText<HTMLButtonElement>(root, 'Send it again', 'button').disabled).toBe(false);
    await click(byText(root, 'Send it again', 'button'));
    expect(f.sent.map((s) => s.redirectTo)).toEqual(['https://arcana.test/diary?claim=tok-1', 'https://arcana.test/diary?claim=tok-1']);
    expect(f.tokens).toEqual(['r1']);
    expect(root.textContent).toContain('Sent again.');
  });

  it('closes with × before anything was sent, and makes no claim token', async () => {
    const onClose = vi.fn();
    const f = fakes();
    const { root } = await mount(sheet(f, { onClose }));
    await click(root.querySelector('button[aria-label="Close"]')!);
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(f.tokens).toEqual([]);
  });

  it('a claim token that could not be made is asked for again at the next send (review M13)', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const f = fakes(null);
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await act(() => {
      vi.advanceTimersByTime(RESEND_WAIT_S * 1000);
    });
    await click(byText(root, 'Send it again', 'button'));
    expect(f.tokens).toEqual(['r1', 'r1']); // a failure is not kept for the whole sheet
    expect(f.sent.map((s) => s.redirectTo)).toEqual(['https://arcana.test/diary', 'https://arcana.test/diary']);
  });

  it('never marks the sign-in as started here for a person who is signed in already (owner decision 15)', async () => {
    localStorage.setItem(SIGNED_IN_KEY, '1'); // e.g. signed in in another tab after the reading was made here
    const f = fakes();
    const { root } = await mount(sheet(f, { google: true }));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(f.sent).toHaveLength(1); // the link still goes out
    await click(byText(root, 'Use another e-mail', 'button'));
    await click(byText(root, 'Continue with Google', 'button'));
    expect(f.sent).toHaveLength(2);
    expect(localStorage.getItem(STARTED_KEY)).toBeNull();
  });

  it('"Use another e-mail" goes back to the form with the focus in the e-mail field (review M15)', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    await click(byText(root, 'Use another e-mail', 'button'));
    expect(document.activeElement).toBe(root.querySelector('input[type="email"]'));
  });

  it('with a claim token the "Check your e-mail" lead says the link opens on any device', async () => {
    const f = fakes();
    const { root } = await mount(sheet(f));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(root.textContent).toContain('Open it on this or any other device to finish.');
    expect(root.textContent).not.toContain('to save this reading');
  });

  it.each([
    ['en', 'Open the link on this device to save this reading.'],
    ['es', 'Abre el enlace en este dispositivo para guardar esta tirada.'],
  ] as const)('without a claim token the lead (%s) says to open the link on this device', async (lang, line) => {
    const f = fakes(null);
    const { root } = await mount(sheet(f, { lang }));
    await typeInto(root.querySelector('input[type="email"]')!, 'ana@example.com');
    await submit(root.querySelector('form')!);
    expect(root.textContent).toContain(line);
    expect(root.textContent).not.toContain('any other device');
    expect(root.textContent).not.toContain('otro dispositivo');
  });

  it('a claim token that never answers times out like a failure: the link goes out without it, Google is off meanwhile', async () => {
    const hangs: FetchFn = (_url, init) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    });
    const f = fakes('tok-1', [], createAccountApi(hangs).claimToken);
    const { root } = await mount(sheet(f, { google: true }));
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] }); // after mount: settle() waits on real timers
    await act(() => {
      const input = root.querySelector('input[type="email"]') as HTMLInputElement;
      input.value = 'ana@example.com';
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(() => {
      root.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(f.sent).toEqual([]); // still waiting for the token
    expect(byText<HTMLButtonElement>(root, 'Continue with Google', 'button').disabled).toBe(true);
    await act(async () => {
      vi.advanceTimersByTime(CREATE_TIMEOUT_MS);
    });
    vi.useRealTimers();
    await settle();
    expect(f.sent.map((s) => s.redirectTo)).toEqual(['https://arcana.test/diary']);
    expect(root.textContent).toContain('Open the link on this device to save this reading.');
  });
});
