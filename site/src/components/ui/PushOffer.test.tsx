// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../../lib/analytics';
import { createPushApi, DENIED_SEEN_KEY, DISMISSED_KEY } from '../../lib/push';
import { byText, cleanup, click, mount, queryText, waitFor } from '../../lib/testing/dom';
import { jsonResponse, routeFetch } from '../../lib/testing/fakes';
import { fakeBrowser, MemoryStorage } from '../../lib/testing/push';
import { PushOffer } from './PushOffer';

vi.mock('../../lib/analytics', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/analytics')>()), sendEvent: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.mocked(sendEvent).mockClear();
});

const KEY = 'BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM';
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 Version/18.1 Mobile/15E148 Safari/604.1';

function api() {
  const served = routeFetch({
    'GET /api/push/key': () => jsonResponse(200, { enabled: true, public_key: KEY }),
    'POST /api/push/subscription': (call) => jsonResponse(201, { hour: (call.body as { hour: number }).hour, tz: 'UTC' }),
    'DELETE /api/push/subscription': () => jsonResponse(204, null),
  });
  return { served, api: createPushApi(served.fetch) };
}

describe('"Remind me each morning" (stage 8.1 §2.5)', () => {
  it('comes after the third day in a row, at 8:00 by default, and turns on at the chosen hour', async () => {
    const browser = fakeBrowser();
    const { served, api: pushApi } = api();
    const { root } = await mount(<PushOffer lang="en" streak={3} env={browser.env} api={pushApi} storage={new MemoryStorage()} />);
    await waitFor(() => expect(root.querySelector('#push-hour')).not.toBeNull());
    const select = root.querySelector<HTMLSelectElement>('#push-hour')!;
    expect(select.value).toBe('8');
    expect(select.options[8].textContent).toBe('8:00 AM');
    await act(() => {
      select.value = '7';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await click(byText(root, 'Remind me each morning', 'button'));
    await waitFor(() => expect(root.querySelector('.push')!.textContent).toBe('Morning reminder on, at 7:00 AM. Turn off'));
    expect((served.calls.find((c) => c.method === 'POST')!.body as { hour: number }).hour).toBe(7);
    expect(vi.mocked(sendEvent)).toHaveBeenCalledWith({ name: 'push_enabled', tool: 'daily', lang: 'en', params: {} });
  });

  it('before the third day there is no offer', async () => {
    const { api: pushApi } = api();
    const { root } = await mount(<PushOffer lang="en" streak={2} env={fakeBrowser().env} api={pushApi} storage={new MemoryStorage()} />);
    expect(root.textContent).toBe('');
  });

  it('when it is on, it says so at any streak and turns off in the same place', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const { served, api: pushApi } = api();
    const storage = new MemoryStorage();
    storage.setItem('ad_push_hour', '6');
    storage.setItem('ad_push_refreshed', '2000-01-01');
    const { root } = await mount(<PushOffer lang="es" streak={1} env={browser.env} api={pushApi} storage={storage} />);
    await waitFor(() => byText(root, 'Desactivar', 'button'));
    expect(root.textContent).toContain('Aviso de la mañana activado, a las 6:00');
    await click(byText(root, 'Desactivar', 'button'));
    expect(served.calls.map((c) => c.method)).toEqual(['POST', 'DELETE']); // the daily refresh, then off
    expect(browser.unsubscribed).toBe(1);
  });

  it('"Not now" hides it on this device', async () => {
    const storage = new MemoryStorage();
    const { root } = await mount(<PushOffer lang="en" streak={5} env={fakeBrowser().env} api={api().api} storage={storage} now={() => 1000} />);
    await waitFor(() => byText(root, 'Not now', 'button'));
    await click(byText(root, 'Not now', 'button'));
    expect(storage.getItem(DISMISSED_KEY)).toBe('1000');
    expect(queryText(root, 'Remind me each morning')).toBeNull();
  });

  it('on an iPhone outside the Home Screen app: the hint, no button', async () => {
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ userAgent: IPHONE }).env} api={api().api} storage={new MemoryStorage()} />);
    expect(root.textContent).toContain('add this site to your Home Screen');
    expect(queryText(root, 'Remind me each morning', 'button')).toBeNull();
  });

  it('a browser where notifications are blocked says where to change it', async () => {
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ permission: 'denied' }).env} api={api().api} storage={new MemoryStorage()} />);
    expect(root.textContent).toBe('Notifications for this site are blocked in your browser settings.');
  });

  it('fetches the key when the offer appears, so the tap goes straight to the permission prompt (review I2)', async () => {
    const browser = fakeBrowser();
    const { served, api: pushApi } = api();
    const { root } = await mount(<PushOffer lang="en" streak={3} env={browser.env} api={pushApi} storage={new MemoryStorage()} />);
    await waitFor(() => expect(served.calls.map((c) => c.url)).toEqual(['/api/push/key']));
    await click(byText(root, 'Remind me each morning', 'button'));
    await waitFor(() => expect(root.querySelector('.push')!.textContent).toContain('Morning reminder on'));
    expect(served.calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/push/key', 'POST /api/push/subscription']);
  });

  it('a failed key request shows the failure line and keeps the offer (review I5)', async () => {
    const served = routeFetch({ 'GET /api/push/key': () => jsonResponse(503, { detail: 'down' }) });
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser().env} api={createPushApi(served.fetch)} storage={new MemoryStorage()} />);
    await waitFor(() => byText(root, 'Remind me each morning', 'button'));
    await click(byText(root, 'Remind me each morning', 'button'));
    await waitFor(() => byText(root, "We couldn't turn on the reminder. Please try again."));
    expect(byText(root, 'Remind me each morning', 'button')).toBeTruthy();
  });

  it('a server with reminders switched off shows no offer', async () => {
    const served = routeFetch({ 'GET /api/push/key': () => jsonResponse(200, { enabled: false, public_key: '' }) });
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser().env} api={createPushApi(served.fetch)} storage={new MemoryStorage()} />);
    await waitFor(() => expect(root.textContent).toBe(''));
  });

  it('closing the permission prompt without a choice shows no error and keeps the offer', async () => {
    const { root } = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ answer: 'default' }).env} api={api().api} storage={new MemoryStorage()} />);
    await waitFor(() => byText(root, 'Remind me each morning', 'button'));
    await click(byText(root, 'Remind me each morning', 'button'));
    expect(root.querySelector('[role="alert"]')).toBeNull();
    expect(byText(root, 'Remind me each morning', 'button')).toBeTruthy();
  });

  it('the "blocked" line comes once, not on every visit', async () => {
    const storage = new MemoryStorage();
    const first = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ permission: 'denied' }).env} api={api().api} storage={storage} />);
    expect(first.root.textContent).toContain('blocked');
    expect(storage.getItem(DENIED_SEEN_KEY)).toBe('1');
    first.unmount();
    const second = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ permission: 'denied' }).env} api={api().api} storage={storage} />);
    await waitFor(() => expect(second.root.textContent).toBe(''));
  });

  it('the blocked line is not used up before the offer would have been shown', async () => {
    const storage = new MemoryStorage();
    await mount(<PushOffer lang="en" streak={1} env={fakeBrowser({ permission: 'denied' }).env} api={api().api} storage={storage} />);
    expect(storage.getItem(DENIED_SEEN_KEY)).toBeNull();
  });

  it('shows the hour the server answers with, and just "on" when this browser does not know it (review M8)', async () => {
    const stale = new MemoryStorage();
    stale.setItem('ad_push_hour', '6');
    stale.setItem('ad_push_refreshed', '2000-01-01');
    const { api: pushApi } = api(); // answers the POST with the hour sent: 6
    const withHour = await mount(<PushOffer lang="en" streak={1} env={fakeBrowser({ permission: 'granted', subscribed: true }).env} api={pushApi} storage={stale} />);
    await waitFor(() => expect(withHour.root.textContent).toContain('Morning reminder on, at 6:00 AM.'));
    withHour.unmount();
    const served = routeFetch({});
    const none = await mount(<PushOffer lang="en" streak={1} env={fakeBrowser({ permission: 'granted', subscribed: true }).env}
      api={createPushApi(served.fetch)} storage={new MemoryStorage()} />);
    await waitFor(() => byText(none.root, 'Turn off', 'button'));
    expect(none.root.textContent).toBe('Morning reminder on. Turn off');
    expect(served.calls).toEqual([]);
  });

  it('the iPhone hint tells that the Home Screen app has its own sign-in; nothing on iOS before 16.4', async () => {
    const hint = await mount(<PushOffer lang="es" streak={3} env={fakeBrowser({ userAgent: IPHONE }).env} api={api().api} storage={new MemoryStorage()} />);
    expect(hint.root.textContent).toContain('tiene su propia sesión');
    hint.unmount();
    const old = await mount(<PushOffer lang="en" streak={3} env={fakeBrowser({ userAgent: IPHONE.replace('18_1', '16_3') }).env}
      api={api().api} storage={new MemoryStorage()} />);
    expect(old.root.textContent).toBe('');
  });
});
