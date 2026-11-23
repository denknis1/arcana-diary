// JSON-LD of the pages (spec stage 6 §3): BreadcrumbList wherever there are breadcrumbs; FAQPage from the FAQ; the
// card page an Article (author and publisher: the Organization "Arcana Diary"; dateModified = reviewed_at; the
// editor a Person; isBasedOn: Waite's book on Wikisource) whose WebPage carries reviewedBy — schema.org defines
// reviewedBy on WebPage, not on Article; hubs a CollectionPage with an ItemList; tools and text pages a WebPage.
import type { Crumb } from './breadcrumbs';
import { absoluteUrl } from './seo';
import type { FaqItem } from './textPages';
import type { Lang } from './types';

export type JsonLd = Readonly<Record<string, unknown>>;

export interface LdItem {
  name: string;
  path: string;
}

interface PageInfo {
  name: string;
  description: string;
  path: string;
  lang: Lang;
}

const CONTEXT = 'https://schema.org';

export const ORGANIZATION = { '@type': 'Organization', name: 'Arcana Diary', url: absoluteUrl('/') } as const;

export const WAITE_BOOK = {
  '@type': 'Book', name: 'The Pictorial Key to the Tarot', author: { '@type': 'Person', name: 'Arthur Edward Waite' },
  datePublished: '1911', url: 'https://en.wikisource.org/wiki/The_Pictorial_Key_to_the_Tarot',
} as const;

const WEBSITE = { '@type': 'WebSite', name: 'Arcana Diary', url: absoluteUrl('/') } as const;

export function breadcrumbLd(crumbs: readonly Crumb[]): JsonLd | null {
  if (crumbs.length === 0) return null;
  return {
    '@context': CONTEXT, '@type': 'BreadcrumbList',
    itemListElement: crumbs.map((c, i) => ({ '@type': 'ListItem', position: i + 1, name: c.name, item: absoluteUrl(c.path) })),
  };
}

export function faqLd(items: readonly FaqItem[]): JsonLd | null {
  if (items.length === 0) return null;
  return {
    '@context': CONTEXT, '@type': 'FAQPage',
    mainEntity: items.map((f) => ({ '@type': 'Question', name: f.q, acceptedAnswer: { '@type': 'Answer', text: f.a } })),
  };
}

export function webPageLd(p: PageInfo): JsonLd {
  return { '@context': CONTEXT, '@type': 'WebPage', name: p.name, description: p.description, url: absoluteUrl(p.path),
    inLanguage: p.lang, isPartOf: WEBSITE };
}

export function collectionLd(p: PageInfo & { items: readonly LdItem[] }): JsonLd {
  return {
    '@context': CONTEXT, '@type': 'CollectionPage', name: p.name, description: p.description, url: absoluteUrl(p.path),
    inLanguage: p.lang, isPartOf: WEBSITE,
    mainEntity: { '@type': 'ItemList', numberOfItems: p.items.length,
      itemListElement: p.items.map((it, i) => ({ '@type': 'ListItem', position: i + 1, name: it.name, url: absoluteUrl(it.path) })) },
  };
}

export function cardLd(p: { headline: string; description: string; path: string; lang: Lang; image: string;
  reviewedAt: string; editorName: string }): JsonLd {
  const editor = { '@type': 'Person', name: p.editorName, jobTitle: 'Editor' };
  return {
    '@context': CONTEXT, '@type': 'Article', headline: p.headline, description: p.description, inLanguage: p.lang,
    image: absoluteUrl(p.image), author: ORGANIZATION, publisher: ORGANIZATION, dateModified: p.reviewedAt, editor,
    isBasedOn: WAITE_BOOK,
    mainEntityOfPage: { '@type': 'WebPage', '@id': absoluteUrl(p.path), url: absoluteUrl(p.path), reviewedBy: editor,
      lastReviewed: p.reviewedAt },
  };
}

/** The text of a <script type="application/ld+json">: no "<", ">" or "&" that could close it or start markup. */
export function ldScript(data: JsonLd): string {
  return JSON.stringify(data).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
}
