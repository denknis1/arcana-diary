import { describe, expect, it } from 'vitest';
import { breadcrumbLd, cardLd, collectionLd, faqLd, ldScript, webPageLd } from './jsonld';

describe('JSON-LD (spec stage 6 §3)', () => {
  it('lists the breadcrumbs with absolute addresses, nothing for a page without them', () => {
    expect(breadcrumbLd([{ name: 'Home', path: '/' }, { name: 'Cards', path: '/cards' }])).toEqual({
      '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://arcanadiary.com/' },
        { '@type': 'ListItem', position: 2, name: 'Cards', item: 'https://arcanadiary.com/cards' }],
    });
    expect(breadcrumbLd([])).toBeNull();
  });

  it('turns the FAQ into FAQPage, nothing for a page without questions', () => {
    expect(faqLd([{ q: 'Is it free?', a: 'Yes.' }])).toEqual({ '@context': 'https://schema.org', '@type': 'FAQPage',
      mainEntity: [{ '@type': 'Question', name: 'Is it free?', acceptedAnswer: { '@type': 'Answer', text: 'Yes.' } }] });
    expect(faqLd([])).toBeNull();
  });

  it('describes a tool as a WebPage and a hub as a CollectionPage with its list', () => {
    expect(webPageLd({ name: 'Yes or no tarot', description: 'D', path: '/yes-no', lang: 'en' })).toEqual({
      '@context': 'https://schema.org', '@type': 'WebPage', name: 'Yes or no tarot', description: 'D',
      url: 'https://arcanadiary.com/yes-no', inLanguage: 'en',
      isPartOf: { '@type': 'WebSite', name: 'Arcana Diary', url: 'https://arcanadiary.com/' } });
    const hub = collectionLd({ name: 'Cartas', description: 'D', path: '/es/cartas', lang: 'es',
      items: [{ name: 'El Loco', path: '/es/cartas/el-loco' }] });
    expect(hub['@type']).toBe('CollectionPage');
    expect(hub.mainEntity).toEqual({ '@type': 'ItemList', numberOfItems: 1, itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'El Loco', url: 'https://arcanadiary.com/es/cartas/el-loco' }] });
  });

  it('describes a card page as an Article by the Organization, edited and reviewed by the editor', () => {
    const ld = cardLd({ headline: 'The Moon Tarot Card Meaning', description: 'D', path: '/cards/the-moon', lang: 'en',
      image: '/cards/the-moon.webp', reviewedAt: '2026-11-23', editorName: 'Adrian Solenne' });
    const editor = { '@type': 'Person', name: 'Adrian Solenne', jobTitle: 'Editor' };
    const org = { '@type': 'Organization', name: 'Arcana Diary', url: 'https://arcanadiary.com/' };
    expect(ld).toMatchObject({ '@type': 'Article', headline: 'The Moon Tarot Card Meaning', inLanguage: 'en',
      image: 'https://arcanadiary.com/cards/the-moon.webp', author: org, publisher: org, dateModified: '2026-11-23',
      editor, isBasedOn: { '@type': 'Book', name: 'The Pictorial Key to the Tarot', datePublished: '1911',
        url: 'https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot' } });
    expect(ld.mainEntityOfPage).toEqual({ '@type': 'WebPage', '@id': 'https://arcanadiary.com/cards/the-moon',
      url: 'https://arcanadiary.com/cards/the-moon', reviewedBy: editor, lastReviewed: '2026-11-23' });
  });

  it('writes script text that cannot close the script or start markup', () => {
    const text = ldScript({ name: '</script><b>&\u2028' });
    expect(text).toBe('{"name":"\\u003c/script\\u003e\\u003cb\\u003e\\u0026\\u2028"}');
    expect(JSON.parse(text)).toEqual({ name: '</script><b>&\u2028' });
  });
});
