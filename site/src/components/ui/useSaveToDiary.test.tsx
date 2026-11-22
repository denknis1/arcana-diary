// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AccountApi } from '../../lib/accountApi';
import type { AnalyticsEvent } from '../../lib/analytics';
import type { Auth } from '../../lib/auth';
import type { AuthConfig } from '../../lib/authConfig';
import { panelConfig } from '../../lib/panel';
import { SHEET_STATE } from '../../lib/sheetHistory';
import { byText, cleanup, click, mount, queryText, waitFor } from '../../lib/testing/dom';
import { ONE, shown } from '../../lib/testing/night';
import { NightRoom } from './NightRoom';
import { useSaveToDiary, type SaveToDiaryOptions } from './useSaveToDiary';

const ON: AuthConfig = { enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: false };
const STATE = shown(ONE, { headline: 'Slow down.' });
const ROOM = { arcanaNight: true }; // the room's own history entry (ReadingIsland)

function fakes(config: AuthConfig | null = ON) {
  const events: AnalyticsEvent[] = [];
  let reads = 0;
  const auth: Auth = {
    session: async () => null, token: async () => null, refresh: async () => null,
    sendLink: async () => ({ ok: true as const }), google: async () => ({ ok: true as const }), signOut: async () => {},
  };
  const accountApi: Pick<AccountApi, 'claimToken'> = {
    claimToken: async () => ({ ok: true, status: 201, data: { token: 'tok-1', expires_at: '2026-11-29T00:00:00Z' } }),
  };
  const options = (extra: Partial<SaveToDiaryOptions> = {}): SaveToDiaryOptions => ({
    lang: 'en', tool: 'love', readingId: 'r1', signedIn: false, accountApi, origin: 'https://arcana.test',
    readConfig: async () => { reads += 1; return config; }, loadAuth: async () => auth,
    send: (event) => { events.push(event); }, ...extra,
  });
  return { events, reads: () => reads, options };
}

/** What ReadingIsland does with the hook: its slot and its sheet in the real night room. */
function Room({ options, onClose = () => {} }: { options: SaveToDiaryOptions; onClose?: (steps: number) => void }) {
  const saving = useSaveToDiary(options);
  const noop = () => {};
  return (
    <>
      <NightRoom state={STATE} lang="en" config={panelConfig('one_card', 'en')} threeCards={false} question="Will it work?"
        sourceName={null} onClose={noop} onRetry={noop} onRestore={noop} onRestoreFollowup={noop} onFollowup={noop}
        onConfirmFollowup={noop} onCancelFollowup={noop} onMoreAbout={noop} onAskAnother={noop}
        save={saving.slot} sheet={saving.sheet} onCloseSheet={saving.closeSheet} />
      <button type="button" onClick={() => onClose(saving.closeForRoom())}>Close the room</button>
    </>
  );
}

/** The phone's Back: the browser is on the entry below and tells the page. */
async function backTo(state: unknown) {
  history.replaceState(state, '');
  await act(() => {
    window.dispatchEvent(new PopStateEvent('popstate', { state }));
  });
}

beforeEach(() => history.replaceState(ROOM, '', '/love'));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Save to diary in the night room (spec 4.4b §4)', () => {
  it('reads the sign-in settings once the reading exists and counts save_click when the sheet opens', async () => {
    const none = fakes();
    const before = await mount(<Room options={none.options({ readingId: null })} />);
    expect(none.reads()).toBe(0);
    expect(queryText(before.root, 'Save to diary', 'button')).toBeNull();
    before.unmount();
    const f = fakes();
    const { root } = await mount(<Room options={f.options()} />);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    expect(f.reads()).toBe(1);
    await click(byText(root, 'Save to diary', 'button'));
    expect(f.events).toEqual([{ name: 'save_click', tool: 'love', lang: 'en', params: {} }]);
    expect(root.querySelector('.night .sheet')).not.toBeNull();
  });

  it('signed in: "Saved to your diary ✓" with the entry link; sign-in off: no button at all', async () => {
    const signed = await mount(<Room options={fakes().options({ signedIn: true })} />);
    await waitFor(() => byText(signed.root, 'Saved to your diary ✓', 'a'));
    expect(byText<HTMLAnchorElement>(signed.root, 'Saved to your diary ✓', 'a').getAttribute('href')).toBe('/diary?r=r1');
    signed.unmount();
    const off = fakes({ enabled: false, supabase_url: '', anon_key: '', google: false });
    const { root } = await mount(<Room options={off.options()} />);
    await waitFor(() => off.reads() === 1);
    expect(queryText(root, 'Save to diary', 'button')).toBeNull();
  });

  it("the sheet is a history entry of its own: the phone's Back closes only the sheet (owner decision 14)", async () => {
    const push = vi.spyOn(history, 'pushState');
    const back = vi.spyOn(history, 'back').mockImplementation(() => {});
    const { root } = await mount(<Room options={fakes().options()} />);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    await click(byText(root, 'Save to diary', 'button'));
    expect(push).toHaveBeenCalledWith(SHEET_STATE, '');
    await backTo(ROOM);
    expect(root.querySelector('.sheet')).toBeNull();
    expect(byText(root, 'Slow down.')).toBeTruthy(); // the room and its answer stay
    expect(back).not.toHaveBeenCalled();
    expect(document.activeElement?.textContent).toBe('Save to diary');
  });

  it('× and Escape take the entry back once; the room closing with the sheet open steps over both', async () => {
    vi.spyOn(history, 'pushState');
    const back = vi.spyOn(history, 'back').mockImplementation(() => {});
    const steps: number[] = [];
    const { root } = await mount(<Room options={fakes().options()} onClose={(n) => steps.push(n)} />);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    await click(byText(root, 'Save to diary', 'button'));
    await click(root.querySelector('.sheet button[aria-label="Close"]')!);
    expect(back).toHaveBeenCalledTimes(1);
    expect(root.querySelector('.sheet')).toBeNull();
    await backTo(ROOM); // the popstate of that back(): nothing more happens
    expect(back).toHaveBeenCalledTimes(1);
    await click(byText(root, 'Save to diary', 'button'));
    await act(() => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    });
    expect(back).toHaveBeenCalledTimes(2);
    expect(root.querySelector('.sheet')).toBeNull();
    await click(byText(root, 'Save to diary', 'button'));
    await click(byText(root, 'Close the room', 'button'));
    expect(steps).toEqual([1]); // ReadingIsland then steps back over the sheet's entry and the room's in one go
    expect(back).toHaveBeenCalledTimes(2);
    expect(root.querySelector('.sheet')).toBeNull();
  });
});
