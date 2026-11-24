// @vitest-environment happy-dom
// ReadingIsland after the review of Task 13: a reload leaves no dead history entry; "Saved to your diary ✓" shows only
// when the create request really carried the token.
import { act } from 'preact/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Api, CreateResult } from '../lib/api';
import { SIGNED_IN_KEY } from '../lib/authState';
import { byText, cleanup, click, mount, queryText, typeInto, waitFor } from '../lib/testing/dom';
import { ONE } from '../lib/testing/night';

let created: CreateResult = { type: 'reading', reading: ONE };

const fakeApi = {
  createReading: async () => created,
  streamReading: async (_id: string, _tz: string | undefined, onEvent: (e: { event: string; data: unknown }) => void) => {
    onEvent({ event: 'meta', data: { soft_line: null } });
    onEvent({ event: 'section', data: { name: 'headline' } });
    onEvent({ event: 'text', data: { name: 'headline', text: 'Slow down.' } });
    onEvent({ event: 'done', data: { answer_shown: 'model' } });
    return { type: 'ended' as const };
  },
  retryReading: async () => ({ type: 'ended' as const }),
  getReading: async () => ({ ok: true as const, status: 200, data: { status: 'done', followups_left: 2, followup_attempts_left: 8 } }),
} as unknown as Api;

vi.mock('../lib/siteApi', () => ({
  siteApi: () => fakeApi,
  siteFetch: () => async () => new Response('{}', { status: 500 }),
}));
vi.mock('../lib/authConfig', () => ({
  authConfig: async () => ({ enabled: true, supabase_url: 'https://abc.supabase.co', anon_key: 'sb_publishable_x', google: false }),
}));
vi.mock('../lib/auth', () => ({ getAuth: async () => null }));
vi.mock('../lib/analytics', async (original) => ({ ...(await original<typeof import('../lib/analytics')>()), sendEvent: () => {} }));

import { t } from '../i18n';
import { openPagePath } from '../lib/textPages';
import ReadingIsland from './ReadingIsland';

const island = () => <ReadingIsland lang="en" page="love" />;

async function draw(root: HTMLElement) {
  await typeInto(root.querySelector('input[type="text"]')!, 'Will it work?');
  await click(byText(root, 'Draw for love', 'button'));
}

beforeEach(() => {
  created = { type: 'reading', reading: ONE };
  history.replaceState(null, '', '/love');
  vi.stubGlobal('matchMedia', () => ({ matches: true })); // reduced motion: the cards arrive turned
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('ReadingIsland: a reload leaves no dead history entry', () => {
  it.each([
    ['the room entry', { arcanaNight: true }],
    ['the room entry with the sheet flag', { arcanaNight: true, arcanaSheet: true }],
  ])('%s of the page before the reload is cleared at mount', async (_name, state) => {
    history.replaceState(state, '', '/love');
    await mount(island());
    expect(history.state).toBeNull();
  });

  it('leaves another state alone', async () => {
    history.replaceState({ other: 1 }, '', '/love');
    await mount(island());
    expect(history.state).toEqual({ other: 1 });
  });

  it('after the clear, a draw and Back close the room (the Back is not swallowed)', async () => {
    history.replaceState({ arcanaNight: true }, '', '/love');
    const { root } = await mount(island());
    await draw(root);
    expect(root.querySelector('.night')).not.toBeNull();
    expect(history.state).toEqual({ arcanaNight: true });
    history.replaceState(null, ''); // the phone's Back: the entry below, which is the cleared one
    await act(() => {
      window.dispatchEvent(new PopStateEvent('popstate', { state: null }));
    });
    expect(root.querySelector('.night')).toBeNull();
  });
});

describe('ReadingIsland: "Saved to your diary ✓" reflects the request', () => {
  it('the flag is set but the create request went without the token: the button, not "Saved"', async () => {
    localStorage.setItem(SIGNED_IN_KEY, '1');
    const { root } = await mount(island());
    await draw(root);
    await waitFor(() => byText(root, 'Save to diary', 'button'));
    expect(queryText(root, 'Saved to your diary ✓')).toBeNull();
  });

  it('the create request carried the token: "Saved to your diary ✓"', async () => {
    localStorage.setItem(SIGNED_IN_KEY, '1');
    created = { type: 'reading', reading: ONE, authed: true };
    const { root } = await mount(island());
    await draw(root);
    await waitFor(() => byText(root, 'Saved to your diary ✓', 'a'));
  });
});

describe('ReadingIsland: the AI provider line under the question field (spec 4.9 §1)', () => {
  it.each([
    ['en', 'home'], ['en', 'one_card'], ['en', 'yes_no'], ['en', 'love'],
    ['es', 'home'], ['es', 'one_card'], ['es', 'yes_no'], ['es', 'love'],
  ] as const)('%s %s shows the line right after the question field', async (lang, page) => {
    const { root } = await mount(<ReadingIsland lang={lang} page={page} />);
    const line = root.querySelector('.provider-line')!;
    expect(line.textContent).toBe(t(lang).providerLine);
    expect(line.previousElementSibling).toBe(root.querySelector('input[type="text"]'));
    expect(line.querySelector('a')).toBeNull(); // no link until the privacy page is published (stage 6)
  });
});

describe('ReadingIsland: the privacy link at the AI provider line (spec stage 6 §6)', () => {
  it('links the policy when the page is open', async () => {
    const { root } = await mount(<ReadingIsland lang="en" page="love" privacyHref="/privacy" />);
    expect(byText<HTMLAnchorElement>(root, t('en').privacyLink, 'a').getAttribute('href')).toBe('/privacy');
  });

  it('shows no link while the page is hidden', async () => {
    const { root } = await mount(island());
    expect(queryText(root, t('en').privacyLink, 'a')).toBeNull();
  });

  it('follows the page: hidden set — no link, set without it — the link (the views pass openPagePath)', async () => {
    const hrefOf = (hidden: Set<string>) => openPagePath('privacy', 'en', hidden) ?? undefined;
    const closed = await mount(<ReadingIsland lang="en" page="love" privacyHref={hrefOf(new Set(['/privacy']))} />);
    expect(queryText(closed.root, t('en').privacyLink, 'a')).toBeNull();
    cleanup();
    const open = await mount(<ReadingIsland lang="en" page="love" privacyHref={hrefOf(new Set())} />);
    expect(byText<HTMLAnchorElement>(open.root, t('en').privacyLink, 'a').getAttribute('href')).toBe('/privacy');
  });
});

// Owner decision 38: the island hands its tool to the night room, so the links under the drawn card follow the stage 2
// matrix rows of that tool (L-ES-03 and L-ES-23 here; every row is in components/ui/NightRoom.test.tsx).
describe('ReadingIsland: the links under the drawn card follow the tool (stage 2 matrix)', () => {
  it('L-ES-03, L-ES-23: the Spanish love page links the drawn card\'s #amor and its full meaning', async () => {
    history.replaceState(null, '', '/es/amor');
    const { root } = await mount(<ReadingIsland lang="es" page="love" />);
    await typeInto(root.querySelector('input[type="text"]')!, '¿Funcionará?');
    await click(byText(root, t('es').drawLove, 'button'));
    await waitFor(() => byText(root, 'La Luna en el amor', 'a'));
    expect(Array.from(root.querySelectorAll<HTMLAnchorElement>('.more-cards a')).map((a) => [a.getAttribute('href'), a.textContent]))
      .toEqual([['/es/cartas/la-luna#amor', 'La Luna en el amor'], ['/es/cartas/la-luna', 'significado completo']]);
  });
});

describe('ReadingIsland: the 18+ and terms line under the draw button (legal review B3)', () => {
  it.each([['en', 'By continuing you confirm you are 18 or older and accept the Terms and the Privacy policy.'],
    ['es', 'Al continuar confirmas que tienes 18 años o más y aceptas los Términos y el Aviso de privacidad.']] as const)(
    '%s: the line sits right under the draw button, as plain text while the pages are hidden', async (lang, text) => {
      const { root } = await mount(<ReadingIsland lang={lang} page="home" />);
      const line = root.querySelector('.consent-line')!;
      expect(line.textContent).toBe(text);
      expect(line.querySelector('a')).toBeNull();
      expect(line.previousElementSibling).toBe(root.querySelector('.panel-hint'));
      expect(root.querySelector('.panel-hint')!.previousElementSibling).toBe(root.querySelector('button[type="submit"]'));
    });

  it('links only the Terms here: the provider line above already links the privacy page', async () => {
    const { root } = await mount(<ReadingIsland lang="en" page="love" privacyHref="/privacy" termsHref="/terms" />);
    const links = [...root.querySelectorAll('.consent-line a')].map((a) => [a.textContent, a.getAttribute('href')]);
    expect(links).toEqual([['Terms', '/terms']]);
    expect(root.querySelector('.consent-line')!.textContent).toContain('and the Privacy policy.');
    expect([...root.querySelectorAll('form a')].filter((a) => a.getAttribute('href') === '/privacy')).toHaveLength(1);
  });

  it('links only the Terms in Spanish too, one link per address in the form', async () => {
    const { root } = await mount(<ReadingIsland lang="es" page="love" privacyHref="/es/privacidad" termsHref="/es/terminos" />);
    const line = root.querySelector('.consent-line')!;
    expect([...line.querySelectorAll('a')].map((a) => [a.textContent, a.getAttribute('href')])).toEqual([['Términos', '/es/terminos']]);
    expect(line.textContent).toContain('el Aviso de privacidad.');
    const hrefs = [...root.querySelectorAll('form a')].map((a) => a.getAttribute('href'));
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it('shows plain text without links while the Terms page is not open', async () => {
    const { root } = await mount(<ReadingIsland lang="es" page="love" />);
    expect(root.querySelector('.consent-line a')).toBeNull();
  });
});
