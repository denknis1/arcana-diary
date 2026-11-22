// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest';
import { NOTICE_KEY } from '../lib/notice';
import { byText, cleanup, mount } from '../lib/testing/dom';
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

  it('a link with ?account=deleted alone says nothing, and the address is cleaned (review M22)', async () => {
    history.replaceState(null, '', '/?account=deleted');
    const { root } = await mount(<HomeNotice lang="en" />);
    expect(root.textContent).toBe('');
    expect(`${location.pathname}${location.search}`).toBe('/');
  });
});
