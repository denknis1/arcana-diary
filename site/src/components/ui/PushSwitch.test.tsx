// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { createPushApi } from '../../lib/push';
import { byText, cleanup, click, mount, waitFor } from '../../lib/testing/dom';
import { jsonResponse, routeFetch } from '../../lib/testing/fakes';
import { fakeBrowser, MemoryStorage } from '../../lib/testing/push';
import { PushSwitch } from './PushSwitch';

afterEach(() => cleanup());

describe('the morning reminder on the account page (stage 8.1 §2.5)', () => {
  it('shows the hour of this browser and turns it off', async () => {
    const browser = fakeBrowser({ permission: 'granted', subscribed: true });
    const served = routeFetch({ 'DELETE /api/push/subscription': () => jsonResponse(204, null) });
    const storage = new MemoryStorage();
    storage.setItem('ad_push_hour', '9');
    const { root } = await mount(<PushSwitch lang="en" env={browser.env} api={createPushApi(served.fetch)} storage={storage} />);
    await waitFor(() => byText(root, 'Turn off', 'button'));
    expect(root.textContent).toContain('Morning reminder in this browser');
    expect(root.textContent).toContain('On, at 9:00 AM.');
    await click(byText(root, 'Turn off', 'button'));
    await waitFor(() => byText(root, 'Off. You can turn it on under the Card of the Day.'));
    expect(browser.unsubscribed).toBe(1);
  });

  it('says it is off and registers nothing', async () => {
    const browser = fakeBrowser();
    const { root } = await mount(<PushSwitch lang="es" env={browser.env} api={createPushApi(routeFetch({}).fetch)} storage={new MemoryStorage()} />);
    await waitFor(() => byText(root, 'Desactivado. Puedes activarlo debajo de la carta del día.'));
    expect(browser.registered).toEqual([]);
  });

  it('a browser without push shows nothing', async () => {
    const { root } = await mount(<PushSwitch lang="en" env={fakeBrowser({ push: false }).env} api={createPushApi(routeFetch({}).fetch)} storage={null} />);
    expect(root.textContent).toBe('');
  });
});
