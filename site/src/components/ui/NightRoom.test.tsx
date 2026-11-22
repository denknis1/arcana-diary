// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { NightState } from '../../lib/nightRoom';
import { panelConfig } from '../../lib/panel';
import { byText, cleanup, click, mount, queryText } from '../../lib/testing/dom';
import { ONE, shown } from '../../lib/testing/night';
import { NightRoom, type NightRoomProps } from './NightRoom';

function room(state: NightState, extra: Partial<NightRoomProps> = {}) {
  const noop = () => {};
  return (
    <NightRoom state={state} lang="en" config={panelConfig('one_card', 'en')} threeCards={false} question="Will it work?"
      sourceName={null} onClose={noop} onRetry={noop} onRestore={noop} onRestoreFollowup={noop} onFollowup={noop}
      onConfirmFollowup={noop} onCancelFollowup={noop} onMoreAbout={noop} onAskAnother={noop} {...extra} />
  );
}

afterEach(() => cleanup());

describe('the night room and the diary (spec 4.4b §4)', () => {
  it('a guest gets "Save to diary" under the answer, after the other actions (review M14)', async () => {
    const onSave = vi.fn();
    const { root } = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: { saved: false, href: '/diary?r=r1', onSave } }));
    expect(root.querySelector('.night__actions')!.lastElementChild?.textContent).toBe('Save to diary');
    await click(byText(root, 'Save to diary', 'button'));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(queryText(root, 'Saved to your diary ✓')).toBeNull();
  });

  it('a signed-in person sees "Saved to your diary ✓" with the link to the entry', async () => {
    const { root } = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: { saved: true, href: '/diary?r=r1', onSave: vi.fn() } }));
    expect(byText<HTMLAnchorElement>(root, 'Saved to your diary ✓', 'a').getAttribute('href')).toBe('/diary?r=r1');
    expect(queryText(root, 'Save to diary', 'button')).toBeNull();
  });

  it('shows nothing when sign-in is off; with the sheet open Escape closes the sheet, not the room', async () => {
    const off = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: null }));
    expect(queryText(off.root, 'Save to diary', 'button')).toBeNull();
    off.unmount();
    const onClose = vi.fn();
    const onCloseSheet = vi.fn();
    await mount(room(shown(ONE, { headline: 'Slow down.' }), {
      onClose, onCloseSheet, save: { saved: false, href: '/diary?r=r1', onSave: vi.fn() },
      sheet: <div class="sheet"><button type="button">Inside</button></div>,
    }));
    expect(document.querySelector('.night__top')!.hasAttribute('inert')).toBe(true); // review M15
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(onCloseSheet).toHaveBeenCalledTimes(1);
    expect(onClose).not.toHaveBeenCalled();
  });
});
