// @vitest-environment happy-dom
import { useEffect, useState } from 'preact/hooks';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, click, mount, waitFor } from '../../lib/testing/dom';
import { jsonResponse } from '../../lib/testing/fakes';
import { HelpLine } from './HelpLine';

afterEach(() => {
  cleanup();
  localStorage.clear();
  history.replaceState(null, '', '/');
});

// The screen tests of stage 4.4b lean on these properties of happy-dom; each is pinned here first (Fable plan review
// I11), so a difference shows up in this file and not halfway through a screen task.
describe('the DOM test setup (spec 4.4b §9)', () => {
  it('renders a component into a document with the stage address and a storage', async () => {
    const { root, unmount } = await mount(<HelpLine lang="es" />);
    const link = root.querySelector('a')!;
    expect(link.getAttribute('href')).toBe('https://findahelpline.com');
    expect(link.textContent).toBe('Líneas de ayuda gratuitas y confidenciales');
    expect(location.origin).toBe('https://arcana.test');
    localStorage.setItem('x', '1');
    expect(localStorage.getItem('x')).toBe('1');
    unmount();
    expect(document.body.textContent).toBe('');
  });

  it('click() on a checkbox ticks it and fires change (the save sheet, the account switch)', async () => {
    function Box() {
      const [on, setOn] = useState(false);
      return (
        <label>
          <input type="checkbox" checked={on} onChange={(e) => setOn((e.target as HTMLInputElement).checked)} />
          <span>{on ? 'on' : 'off'}</span>
        </label>
      );
    }
    const { root } = await mount(<Box />);
    await click(root.querySelector('input')!);
    expect(root.querySelector('input')!.checked).toBe(true);
    expect(root.querySelector('span')!.textContent).toBe('on');
  });

  it('focus() on a heading with tabIndex -1 moves document.activeElement (focus after a screen change)', async () => {
    const { root } = await mount(<h2 tabIndex={-1}>Check your e-mail</h2>);
    root.querySelector('h2')!.focus();
    expect(document.activeElement?.textContent).toBe('Check your e-mail');
  });

  it('pushState and replaceState change location and history.state (the diary address, the sheet entry)', () => {
    history.pushState({ arcanaNight: true }, '', '/diary?claim=t&remind=1');
    expect(`${location.pathname}${location.search}`).toBe('/diary?claim=t&remind=1');
    expect(history.state).toEqual({ arcanaNight: true });
    history.replaceState(null, '', '/diary');
    expect(`${location.pathname}${location.search}`).toBe('/diary');
    expect(history.state).toBeNull();
  });

  it('Response as the fakes use it: JSON, clone(), an empty 401 whose json() fails', async () => {
    const ok = jsonResponse(200, { a: 1 });
    expect(ok).toBeInstanceOf(Response);
    expect(await ok.clone().json()).toEqual({ a: 1 });
    expect(await ok.json()).toEqual({ a: 1 });
    const stage = new Response('', { status: 401 });
    expect(stage.status).toBe(401);
    await expect(stage.clone().json()).rejects.toThrow();
    expect(typeof fetch).toBe('function');
  });

  it('cleanup() unmounts what is still mounted, so its listeners go; waitFor waits for a condition', async () => {
    const keys: string[] = [];
    function Listener() {
      const [ready, setReady] = useState(false);
      useEffect(() => {
        const onKey = (event: KeyboardEvent) => keys.push(event.key);
        document.addEventListener('keydown', onKey);
        void Promise.resolve().then(() => setReady(true));
        return () => document.removeEventListener('keydown', onKey);
      }, []);
      return <p>{ready ? 'ready' : 'waiting'}</p>;
    }
    const { root } = await mount(<Listener />);
    await waitFor(() => expect(root.textContent).toBe('ready'));
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    cleanup();
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'b' }));
    expect(keys).toEqual(['a']);
    expect(document.body.childElementCount).toBe(0);
    await expect(waitFor(() => false, 50)).rejects.toThrow('waitFor: the check stayed false');
  });
});
