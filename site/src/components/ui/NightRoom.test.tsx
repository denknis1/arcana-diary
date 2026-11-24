// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { NightState } from '../../lib/nightRoom';
import { panelConfig, type PanelPage } from '../../lib/panel';
import { byText, cleanup, click, mount, queryText } from '../../lib/testing/dom';
import { ONE, shown } from '../../lib/testing/night';
import type { DrawnCard, Lang, ReadingCreated, Vote } from '../../lib/types';
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
  // L-EN-32, L-ES-26 (stage 2 matrix, owner decision 42): saving at launch is the reading's, not the Card of the Day's
  it('L-EN-32: a guest gets "Save to diary" right under the answer, the first of its actions (owner decision 41)', async () => {
    const onSave = vi.fn();
    const { root } = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: { saved: false, href: '/diary?r=r1', onSave } }));
    const actions = Array.from(root.querySelector('.night__actions')!.children).map((el) => el.className);
    expect(actions).toEqual(['btn btn--gold', 'more-cards', 'btn btn--text']); // save, the card links, ask another
    expect(root.querySelector('.night__actions')!.firstElementChild?.textContent).toBe('Save to diary');
    await click(byText(root, 'Save to diary', 'button'));
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(queryText(root, 'Saved to your diary ✓')).toBeNull();
  });

  it('a signed-in person sees "Saved to your diary ✓" with the link to the entry', async () => {
    const { root } = await mount(room(shown(ONE, { headline: 'Slow down.' }), { save: { saved: true, href: '/diary?r=r1', onSave: vi.fn() } }));
    expect(byText<HTMLAnchorElement>(root, 'Saved to your diary ✓', 'a').getAttribute('href')).toBe('/diary?r=r1');
    expect(queryText(root, 'Save to diary', 'button')).toBeNull();
  });

  it('L-ES-26: «Guardar en el diario» under the Spanish answer, then «Guardada en tu diario ✓» to the entry', async () => {
    const config = panelConfig('one_card', 'es');
    const guest = await mount(room(shown({ ...ONE, lang: 'es' }, { headline: 'Despacio.' }), {
      lang: 'es', config, save: { saved: false, href: '/es/diario?r=r1', onSave: vi.fn() } }));
    expect(guest.root.querySelector('.night__actions')!.firstElementChild?.textContent).toBe('Guardar en el diario');
    guest.unmount();
    const { root } = await mount(room(shown({ ...ONE, lang: 'es' }, { headline: 'Despacio.' }), {
      lang: 'es', config, save: { saved: true, href: '/es/diario?r=r1', onSave: vi.fn() } }));
    expect(byText<HTMLAnchorElement>(root, 'Guardada en tu diario ✓', 'a').getAttribute('href')).toBe('/es/diario?r=r1');
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

// Owner decision 38 (23.11.2026): the links under the drawn cards follow the launch rows of
// docs/research/stage2/links-{en,es}.csv — tools/site/check_links.py names this file for each row id below.
// Owner decision 41: a compact list of text links, one row per drawn card, not full-width buttons.
describe('links under the drawn cards (stage 2 matrix, owner decisions 38, 41)', () => {
  const card = (card_id: string, name: string, position: DrawnCard['position'], reversed = false, vote?: Vote): DrawnCard =>
    ({ card_id, name, position, reversed, ...(vote ? { vote } : {}) });
  const three = (lang: Lang, kind: ReadingCreated['kind'] = 'three'): ReadingCreated => ({
    id: 'r3', lang, kind, verdict: null, soft_line: null, remaining: 1, cards: lang === 'en'
      ? [card('major-18-moon', 'The Moon', 'past'), card('major-19-sun', 'The Sun', 'present'), card('major-17-star', 'The Star', 'path', true)]
      : [card('major-18-moon', 'La Luna', 'past'), card('major-19-sun', 'El Sol', 'present'), card('major-17-star', 'La Estrella', 'path', true)],
  });
  const one = (lang: Lang, kind: ReadingCreated['kind'] = 'one', verdict: ReadingCreated['verdict'] = null): ReadingCreated => ({
    id: 'r1', lang, kind, verdict, soft_line: null, remaining: 1,
    cards: [card('major-18-moon', lang === 'en' ? 'The Moon' : 'La Luna', 'card')],
  });
  const mountRoom = (reading: ReadingCreated, lang: Lang, page: PanelPage) => mount(room(shown(reading, { headline: 'Slow down.' }), {
    lang, config: panelConfig(page, lang, page === 'card' ? 'major-18-moon' : null), threeCards: reading.cards.length === 3,
  }));
  const links = async (reading: ReadingCreated, lang: Lang, page: PanelPage) => {
    const { root } = await mountRoom(reading, lang, page);
    expect(root.querySelectorAll('.more-cards a.btn')).toHaveLength(0); // text links, no pill buttons
    return Array.from(root.querySelectorAll<HTMLAnchorElement>('.more-cards a'))
      .map((a) => [a.getAttribute('href'), a.textContent]);
  };
  const rows = async (reading: ReadingCreated, lang: Lang, page: PanelPage) => {
    const { root } = await mountRoom(reading, lang, page);
    return Array.from(root.querySelectorAll('.more-cards li')).map((li) => li.textContent);
  };
  const EN_THREE = [['/cards/the-moon', 'The Moon — full meaning'], ['/cards/the-sun', 'The Sun — full meaning'],
    ['/cards/the-star', 'The Star — full meaning']];
  const ES_THREE = [['/es/cartas/la-luna', 'La Luna — significado completo'], ['/es/cartas/el-sol', 'El Sol — significado completo'],
    ['/es/cartas/la-estrella', 'La Estrella — significado completo']];

  it('L-EN-01: the English home (three cards) — "{card_name} — full meaning" under each card', async () => {
    expect(await links(three('en'), 'en', 'home')).toEqual(EN_THREE);
  });

  it('L-EN-02: one card — "{card_name} — full meaning"', async () => {
    expect(await links(one('en'), 'en', 'one_card')).toEqual([['/cards/the-moon', 'The Moon — full meaning']]);
  });

  it('L-EN-03: the love reading — "{card_name} — full meaning" to the card page (#love is L-EN-22, V1.1)', async () => {
    expect(await links(three('en'), 'en', 'love')).toEqual(EN_THREE);
  });

  it('L-EN-31: yes or no, one card and three — "{card_name} — full meaning"', async () => {
    expect(await links(one('en', 'yes_no', { value: 'unclear', label: 'Not clear yet' }), 'en', 'yes_no'))
      .toEqual([['/cards/the-moon', 'The Moon — full meaning']]);
    expect(await links({ ...three('en', 'yes_no'), verdict: { value: 'yes', label: 'Yes' } }, 'en', 'yes_no')).toEqual(EN_THREE);
  });

  it('L-ES-01: the Spanish home, three cards and one (#una-carta) — "{card_name} — significado completo"', async () => {
    expect(await links(three('es'), 'es', 'home')).toEqual(ES_THREE);
    expect(await links(one('es'), 'es', 'home')).toEqual([['/es/cartas/la-luna', 'La Luna — significado completo']]);
  });

  it('L-ES-02: the three-card spread — "{card_name} — significado completo"', async () => {
    expect(await links(three('es'), 'es', 'three_cards')).toEqual(ES_THREE);
  });

  it('L-ES-03, L-ES-23: the love reading — "{card_name} en el amor" to #amor · "significado completo", one row a card', async () => {
    expect(await links(three('es'), 'es', 'love')).toEqual([
      ['/es/cartas/la-luna#amor', 'La Luna en el amor'], ['/es/cartas/la-luna', 'significado completo'],
      ['/es/cartas/el-sol#amor', 'El Sol en el amor'], ['/es/cartas/el-sol', 'significado completo'],
      ['/es/cartas/la-estrella#amor', 'La Estrella en el amor'], ['/es/cartas/la-estrella', 'significado completo'],
    ]);
    expect(await rows(three('es'), 'es', 'love')).toEqual(['La Luna en el amor · significado completo',
      'El Sol en el amor · significado completo', 'La Estrella en el amor · significado completo']);
  });

  it('L-ES-04: sí o no — "Por qué {card_name} dice {verdict}" to #si-o-no, each card with its own vote', async () => {
    // a card that says "not clear yet" asks the short question (owner decision 41)
    expect(await links(one('es', 'yes_no', { value: 'unclear', label: 'Todavía no está claro' }), 'es', 'yes_no'))
      .toEqual([['/es/cartas/la-luna#si-o-no', '¿Por qué La Luna?']]);
    const votes: ReadingCreated = {
      id: 'r3', lang: 'es', kind: 'yes_no', soft_line: null, remaining: 1, verdict: { value: 'yes', label: 'Sí' },
      cards: [card('major-19-sun', 'El Sol', 'card', false, 'yes'), card('major-16-tower', 'La Torre', 'card', false, 'no'),
        card('major-17-star', 'La Estrella', 'card', true, 'unclear')],
    };
    expect(await links(votes, 'es', 'yes_no')).toEqual([
      ['/es/cartas/el-sol#si-o-no', 'Por qué El Sol dice sí'], ['/es/cartas/la-torre#si-o-no', 'Por qué La Torre dice no'],
      ['/es/cartas/la-estrella#si-o-no', '¿Por qué La Estrella?'],
    ]);
  });

  it('L-ES-04 without a verdict (health, legal, safety, another person): no yes or no, the full meaning instead', async () => {
    // the API gives no verdict and no votes; the rule of the deck would say "sí" for El Sol — the link must not
    const sun: ReadingCreated = { ...one('es', 'yes_no'), cards: [card('major-19-sun', 'El Sol', 'card')] };
    expect(await links(sun, 'es', 'yes_no')).toEqual([['/es/cartas/el-sol', 'El Sol — significado completo']]);
    expect(await links({ ...three('es', 'yes_no'), verdict: null }, 'es', 'yes_no')).toEqual(ES_THREE);
    expect(await links({ ...sun, lang: 'en', cards: [card('major-19-sun', 'The Sun', 'card')] }, 'en', 'yes_no'))
      .toEqual([['/cards/the-sun', 'The Sun — full meaning']]);
  });

  it('shows no link to the card of the card page itself (it would reload the page and close the reading)', async () => {
    expect(await links(one('en', 'card_page'), 'en', 'card')).toEqual([]);
    expect(await links(one('es', 'card_page'), 'es', 'card')).toEqual([]);
  });
});
