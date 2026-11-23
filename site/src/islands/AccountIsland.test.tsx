// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createAccountApi, type Account, type AccountApi } from '../lib/accountApi';
import type { Auth, SessionStatus } from '../lib/auth';
import { NOTICE_KEY } from '../lib/notice';
import { byText, cleanup, click, mount, queryText, waitFor } from '../lib/testing/dom';
import { openPagePath } from '../lib/textPages';
import AccountIsland from './AccountIsland';

const ACCOUNT: Account = { email: 'ana@example.com', created_at: '2026-11-20T18:00:00+00:00', reminders_consent: false,
  consent_at: null, limit: 3, used: 1, remaining: 2, day: '2026-11-22' };

const UNAVAILABLE = 'The service is unavailable right now. Please try again in a few minutes.';

function fakes(over: {
  account?: AccountApi['account'];
  setConsent?: AccountApi['setConsent'];
  deleteAccount?: AccountApi['deleteAccount'];
  exportFile?: AccountApi['exportFile'];
  signOut?: () => Promise<void>;
} = {}) {
  const calls: string[] = [];
  const saved: Array<[Blob, string]> = [];
  const navigate = vi.fn();
  const auth = {
    check: async () => ({ type: 'none' as const }),
    session: async () => null, token: async () => 'tok', refresh: async () => null,
    sendLink: async () => ({ ok: true as const }), google: async () => ({ ok: true as const }),
    signOut: vi.fn(over.signOut ?? (async () => { calls.push('signOut'); })),
  } satisfies Auth;
  const api = {
    account: over.account ?? (async () => { calls.push('account'); return { ok: true, status: 200, data: ACCOUNT }; }),
    setConsent: over.setConsent ?? (async (on: boolean) => {
      calls.push(`consent ${on}`);
      return { ok: true, status: 200, data: { email: ACCOUNT.email, reminders_consent: on, consent_at: null } };
    }),
    exportFile: over.exportFile ?? (async () => {
      calls.push('export');
      return { ok: true, blob: new Blob(['{"readings":[]}'], { type: 'application/json' }), filename: 'arcana-diary-2026-11-22.json' };
    }),
    deleteAccount: over.deleteAccount
      ?? (async () => { calls.push('delete'); return { ok: true, status: 200, data: { deleted: true } }; }),
  } as unknown as AccountApi;
  const signedIn = async (): Promise<SessionStatus> => ({ type: 'signedIn', auth, google: false, session: { access_token: 'tok' } });
  const props = { api, navigate, save: (blob: Blob, name: string) => { saved.push([blob, name]); }, session: signedIn,
    signOutWaitMs: 20 };
  return { calls, saved, navigate, auth, props };
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  localStorage.clear();
});

describe('the account page (spec 4.4b §6)', () => {
  it('links the privacy policy under the consent once the policy page is open (stage 6 §6)', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} privacyHref="/privacy" />);
    expect(byText<HTMLAnchorElement>(root, 'Privacy policy', 'a').getAttribute('href')).toBe('/privacy');
  });

  it('follows the page: no link while /privacy is hidden, the link once it is not', async () => {
    const f = fakes();
    const view = (hidden: Set<string>) => (
      <AccountIsland lang="en" {...f.props} privacyHref={openPagePath('privacy', 'en', hidden) ?? undefined} />
    );
    const closed = await mount(view(new Set(['/privacy'])));
    expect(queryText(closed.root, 'Privacy policy', 'a')).toBeNull();
    cleanup();
    const open = await mount(view(new Set()));
    expect(byText<HTMLAnchorElement>(open.root, 'Privacy policy', 'a').getAttribute('href')).toBe('/privacy');
  });

  it('shows the e-mail, the readings left today and the way back to the diary', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    expect(byText(root, 'Signed in as ana@example.com')).toBeTruthy();
    expect(byText(root, 'Readings left today: 2 of 3')).toBeTruthy();
    expect(byText<HTMLAnchorElement>(root, 'Your diary', 'a').getAttribute('href')).toBe('/diary');
  });

  it('the consent switch says the e-mails start later and saves the choice', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    const box = root.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    expect(box.checked).toBe(false);
    expect(root.textContent).toContain("We don't send these e-mails yet; they start later. You can turn them off here at any time.");
    await click(box);
    expect(f.calls).toContain('consent true');
    expect(root.querySelector<HTMLInputElement>('input[type="checkbox"]')!.checked).toBe(true);
  });

  it('a consent that is not saved stays off and says so next to the switch (handoff 10: no optimistic update)', async () => {
    const f = fakes({ setConsent: async () => ({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    const box = root.querySelector<HTMLInputElement>('input[type="checkbox"]')!;
    await click(box);
    expect(root.querySelector<HTMLInputElement>('input[type="checkbox"]')!.checked).toBe(false);
    const consent = root.querySelector('.account__consent')!;
    expect(consent.querySelector('[role="alert"]')?.textContent).toBe(UNAVAILABLE);
    expect(root.querySelectorAll('[role="alert"]')).toHaveLength(1);
  });

  it('downloads all readings as a file', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Download my readings', 'button'));
    expect(f.saved.map(([, name]) => name)).toEqual(['arcana-diary-2026-11-22.json']);
    expect(await f.saved[0][0].text()).toBe('{"readings":[]}');
  });

  it('"Delete account" opens "Delete forever?" with Download and Cancel; Cancel gives focus back', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    const dialog = root.querySelector('[role="alertdialog"]')!;
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(document.getElementById(dialog.getAttribute('aria-labelledby')!)?.textContent).toBe('Delete forever?');
    expect(document.activeElement?.textContent).toBe('Delete forever?');
    expect(dialog.textContent).toContain('This cannot be undone.');
    await click(byText(dialog, 'Download', 'button'));
    expect(f.calls).toContain('export');
    expect(f.saved).toHaveLength(1);
    await click(byText(dialog, 'Cancel', 'button'));
    expect(root.querySelector('[role="alertdialog"]')).toBeNull();
    expect(document.activeElement?.textContent).toBe('Delete account');
    expect(f.calls).not.toContain('delete');
  });

  it('Escape is Cancel: the dialog closes and focus goes back to "Delete account"', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(root.querySelector('[role="alertdialog"]')).toBeNull();
    expect(document.activeElement?.textContent).toBe('Delete account');
  });

  it('"Delete forever" deletes, signs out on this device at once and goes home with the notice', async () => {
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="es" {...f.props} />);
    await click(byText(root, 'Eliminar cuenta', 'button'));
    await click(byText(root, 'Eliminar para siempre', 'button'));
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/es?account=deleted'));
    expect(f.calls.slice(-2)).toEqual(['delete', 'signOut']);
    expect(sessionStorage.getItem(NOTICE_KEY)).toBe('accountDeleted'); // the home page says it once (review M22)
  });

  it('"Sign out" goes home; not signed in shows the sign-in block', async () => {
    const f = fakes();
    const { root, unmount } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Sign out', 'button'));
    expect(f.calls).toContain('signOut');
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/'));
    unmount();
    const out = await mount(<AccountIsland lang="en" {...f.props}
      session={async () => ({ type: 'signedOut', auth: f.auth, google: false })} />);
    expect(out.root.querySelector('input[type="email"]')).not.toBeNull();
  });

  it('a sign-in library that errs is "try again", never the sign-in block, and the flag stays (handoff 9)', async () => {
    const f = fakes();
    localStorage.setItem('ad_signed_in', '1');
    let opens = 0;
    const session = async (): Promise<SessionStatus> => {
      opens += 1;
      return opens === 1 ? { type: 'unreachable' } : f.props.session();
    };
    const { root } = await mount(<AccountIsland lang="en" {...f.props} session={session} />);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe(UNAVAILABLE);
    expect(root.querySelector('input[type="email"]')).toBeNull();
    expect(localStorage.getItem('ad_signed_in')).toBe('1');
    await click(byText(root, 'Try again', 'button'));
    expect(byText(root, 'Signed in as ana@example.com')).toBeTruthy();
  });

  it('only 401 "sign_in" shows the sign-in block; a 401 without JSON is the stage line with a reload button', async () => {
    localStorage.setItem('ad_signed_in', '1');
    const gone = fakes({ account: async () => ({ ok: false, status: 401, error: 'other', body: { reason: 'sign_in' } }) });
    const first = await mount(<AccountIsland lang="en" {...gone.props} />);
    expect(first.root.querySelector('input[type="email"]')).not.toBeNull();
    expect(localStorage.getItem('ad_signed_in')).toBeNull(); // so the block's "started here" mark is set (decision 15)
    first.unmount();
    const stage = fakes({ account: async () => ({ ok: false, status: 401, error: 'stage', body: null }) });
    const { root } = await mount(<AccountIsland lang="en" {...stage.props} />);
    expect(root.querySelector('input[type="email"]')).toBeNull();
    expect(root.querySelector('[role="alert"]')?.textContent)
      .toBe('Your session on this preview site has expired. Reload the page to continue.');
    expect(queryText(root, 'Try again', 'button')).not.toBeNull();
    expect(queryText(root, 'Delete account', 'button')).toBeNull(); // nothing to act on without the account
    expect(queryText(root, 'Download my readings', 'button')).toBeNull();
    expect(queryText(root, 'Sign out', 'button')).not.toBeNull(); // leaving stays possible (review)
  });

  it('an account that does not load (503) still offers "Sign out", and it works offline; Download and Delete stay hidden', async () => {
    const f = fakes({ account: async () => ({ ok: false, status: 503, error: 'unavailable', body: null }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    expect(root.querySelector('[role="alert"]')?.textContent).toBe(UNAVAILABLE);
    expect(queryText(root, 'Delete account', 'button')).toBeNull();
    expect(queryText(root, 'Download my readings', 'button')).toBeNull();
    await click(byText(root, 'Sign out', 'button'));
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/'));
    expect(f.auth.signOut).toHaveBeenCalled();
  });

  it('a deletion that fails says so inside the dialog; nothing is signed out (review I5)', async () => {
    const f = fakes({ deleteAccount: async () => ({ ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    await click(byText(root, 'Delete forever', 'button'));
    const dialog = root.querySelector('[role="alertdialog"]')!;
    expect(dialog.querySelector('[role="alert"]')?.textContent).toBe(UNAVAILABLE);
    expect(root.querySelectorAll('[role="alert"]')).toHaveLength(1); // not also under the page's buttons
    expect(f.auth.signOut).not.toHaveBeenCalled();
    expect(f.navigate).not.toHaveBeenCalled();
    expect(byText(dialog, 'Delete forever', 'button').getAttribute('aria-disabled')).not.toBe('true');
  });

  it('a sign-out that hangs does not hold the person here: home after a short wait (review M6)', async () => {
    const f = fakes({ signOut: () => new Promise<void>(() => {}) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Sign out', 'button'));
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/'));
  });

  it('while the account is being deleted, Escape and Cancel do nothing and focus stays (review M22, handoff 10)', async () => {
    const pending: { finish?: () => void } = {};
    let deletes = 0;
    const f = fakes({ deleteAccount: () => new Promise((resolve) => {
      deletes += 1;
      pending.finish = () => resolve({ ok: true, status: 200, data: { deleted: true } });
    }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    const forever = byText(root, 'Delete forever', 'button');
    forever.focus();
    await click(forever);
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(root.querySelector('[role="alertdialog"]')).not.toBeNull();
    const cancel = byText(root, 'Cancel', 'button');
    expect(cancel.getAttribute('aria-disabled')).toBe('true');
    await click(cancel);
    await click(byText(root, 'Delete forever', 'button'));
    expect(root.querySelector('[role="alertdialog"]')).not.toBeNull();
    expect(deletes).toBe(1);
    expect(document.activeElement?.textContent).toBe('Delete forever'); // aria-disabled keeps the focus in the dialog
    await act(() => {
      pending.finish?.();
    });
    await waitFor(() => expect(f.navigate).toHaveBeenCalledWith('/?account=deleted'));
  });

  const rejectedBlob = () => createAccountApi((async () => ({
    ok: true, status: 200, headers: new Headers(), blob: () => Promise.reject(new TypeError('body dropped')),
  })) as unknown as typeof fetch).exportFile;

  it('a download whose body fails says so next to Download, and the buttons work again (review I1)', async () => {
    const f = fakes({ exportFile: rejectedBlob() });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Download my readings', 'button'));
    expect(root.querySelector('.account__actions ~ .account__error [role="alert"]')).not.toBeNull();
    expect(f.saved).toHaveLength(0);
    for (const label of ['Download my readings', 'Sign out', 'Delete account']) {
      expect(byText(root, label, 'button').getAttribute('aria-disabled')).not.toBe('true');
    }
    await click(byText(root, 'Delete account', 'button'));
    expect(root.querySelector('[role="alertdialog"]')).not.toBeNull(); // not ignored as "busy"
  });

  it('a download whose body fails inside the dialog: the error is there, Cancel and Escape work (review I1)', async () => {
    const f = fakes({ exportFile: rejectedBlob() });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    await click(byText(root, 'Download', 'button'));
    const dialog = root.querySelector('[role="alertdialog"]')!;
    expect(dialog.querySelector('[role="alert"]')).not.toBeNull();
    expect(byText(dialog, 'Cancel', 'button').getAttribute('aria-disabled')).not.toBe('true');
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(root.querySelector('[role="alertdialog"]')).toBeNull();
    await click(byText(root, 'Delete account', 'button'));
    await click(byText(dialog.ownerDocument.body, 'Cancel', 'button'));
    expect(root.querySelector('[role="alertdialog"]')).toBeNull();
  });

  it('a 401 without JSON inside the dialog offers the reload button (review M3)', async () => {
    const reload = vi.spyOn(location, 'reload').mockImplementation(() => {});
    const f = fakes({ exportFile: async () => ({ ok: false, status: 401, error: 'stage' }) });
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    await click(byText(root, 'Delete account', 'button'));
    await click(byText(root, 'Download', 'button'));
    const dialog = root.querySelector<HTMLElement>('[role="alertdialog"]')!;
    expect(dialog.querySelector('[role="alert"]')?.textContent)
      .toBe('Your session on this preview site has expired. Reload the page to continue.');
    await click(byText(dialog, 'Try again', 'button'));
    expect(reload).toHaveBeenCalledTimes(1);
    reload.mockRestore();
  });

  it('while the dialog is open the page behind it is inert; closing lifts it (review M4)', async () => {
    const header = document.createElement('header');
    header.innerHTML = '<button type="button">Menu</button>';
    document.body.prepend(header);
    const f = fakes();
    const { root } = await mount(<AccountIsland lang="en" {...f.props} />);
    expect(header.closest('[inert]')).toBeNull();
    await click(byText(root, 'Delete account', 'button'));
    const dialog = root.querySelector<HTMLElement>('[role="alertdialog"]')!;
    expect(dialog.closest('[inert]')).toBeNull();
    expect(header.closest('[inert]')).not.toBeNull();
    expect(byText(root, 'Sign out', 'button').closest('[inert]')).not.toBeNull();
    await click(byText(dialog, 'Cancel', 'button'));
    expect(document.querySelector('[inert]')).toBeNull();
    expect(byText(root, 'Sign out', 'button').closest('[inert]')).toBeNull();
  });

  it('a page restored from the back/forward cache reloads; the listener goes with the page (review M5)', async () => {
    const reload = vi.spyOn(location, 'reload').mockImplementation(() => {});
    const f = fakes();
    const { unmount } = await mount(<AccountIsland lang="en" {...f.props} />);
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
    reload.mockRestore();
  });
});
