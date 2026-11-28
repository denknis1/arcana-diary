// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { sendEvent } from '../../lib/analytics';
import { createPushApi, DISMISSED_KEY } from '../../lib/push';
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
});
