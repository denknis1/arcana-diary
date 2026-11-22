// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { NightState } from '../../lib/nightRoom';
import { panelConfig } from '../../lib/panel';
import { byText, cleanup, click, mount, queryText } from '../../lib/testing/dom';
import { ONE, shown } from '../../lib/testing/night';
import type { ReadingCreated } from '../../lib/types';
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

  it('shows each of three yes/no cards with its own vote, icon and word, and the verdict (spec 4.5 §4)', async () => {
    const yesNo: ReadingCreated = {
      id: 'r3', lang: 'en', kind: 'yes_no', soft_line: null, remaining: 1, verdict: { value: 'yes', label: 'Yes' },
      cards: [
        { card_id: 'major-19-sun', position: 'card', reversed: false, name: 'The Sun', vote: 'yes' },
        { card_id: 'major-16-tower', position: 'card', reversed: false, name: 'The Tower', vote: 'no' },
        { card_id: 'major-17-star', position: 'card', reversed: true, name: 'The Star', vote: 'unclear' },
      ],
    };
    const state = shown(yesNo, { headline: 'Leaning yes.', card1: 'Warm.', card2: 'A jolt.', card3: 'Wait.', why: 'Two decide.' });
    const { root } = await mount(room(state, { threeCards: true, config: panelConfig('yes_no', 'en') }));
    const votes = Array.from(root.querySelectorAll('.spread__vote'));
    expect(votes.map((v) => v.textContent)).toEqual(['Yes', 'No', 'Not clear yet']);
    expect(votes.every((v) => v.querySelector('svg[aria-hidden="true"]') !== null)).toBe(true);
    expect(root.querySelector('.verdict__word')?.textContent).toBe('Yes');
    expect(root.textContent).toContain('Why: Two decide.');
    expect(root.querySelectorAll('.spread__pos')).toHaveLength(0); // no past · present · path on yes/no
  });
});
