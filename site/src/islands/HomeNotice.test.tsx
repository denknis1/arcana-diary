// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { NOTICE_KEY } from '../lib/notice';
import { render } from 'preact';
import { byText, cleanup, mount, settle } from '../lib/testing/dom';
import HomeNotice from './HomeNotice';

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});

describe('the home page notice (spec 4.4b §6)', () => {
  it('says once that the account was deleted and cleans the address', async () => {
    sessionStorage.setItem(NOTICE_KEY, 'accountDeleted'); // left by the account page right before it came here
    history.replaceState(null, '', '/es?account=deleted&utm_source=x');
    const { root } = await mount(<HomeNotice lang="es" />);
    expect(byText(root, 'Tu cuenta se eliminó.').getAttribute('role')).toBe('status');
    expect(`${location.pathname}${location.search}`).toBe('/es?utm_source=x');
    expect(sessionStorage.getItem(NOTICE_KEY)).toBeNull();
  });

  it('the status container is in the page empty first and filled after, so a screen reader announces it (review M6)', async () => {
    sessionStorage.setItem(NOTICE_KEY, 'accountDeleted');
    history.replaceState(null, '', '/?account=deleted');
    const root = document.createElement('div');
    document.body.appendChild(root);
    render(<HomeNotice lang="en" />, root);
    const live = root.querySelector('[role="status"]');
    expect(live).not.toBeNull();
    expect(live?.textContent).toBe('');
    await mount(<span />); // lets the timers run
    await settle();
    expect(root.querySelector('[role="status"]')).toBe(live); // the same node, now filled
    expect(live?.textContent).toBe('Your account has been deleted.');
    render(null, root);
  });

  it('a link with ?account=deleted alone says nothing, and the address is cleaned (review M22)', async () => {
    history.replaceState(null, '', '/?account=deleted');
    const { root } = await mount(<HomeNotice lang="en" />);
    expect(root.textContent).toBe('');
    expect(`${location.pathname}${location.search}`).toBe('/');
  });
});
