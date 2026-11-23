// The stage 5 texts of the tool, hub and service pages (content/pages, copied to src/data/pages by
// tools/site/sync_site_data.py). A service page with a placeholder that has no value in the facts is built but
// hidden — noindex, outside the menu, the footer and the sitemap (owner decision 35); any other page with such a
// placeholder stops the build.
import { FACTS, fillFacts, missingFacts, type Facts } from './facts';
import { pagePath, type PageKey } from './routes';
import type { Lang } from './types';

export interface TextBlock {
  id: string;
  heading: string;
  paragraphs: string[];
}

export interface FaqItem {
  q: string;
  a: string;
}

export interface TextPage {
  page_id: string;
  lang: Lang;
  url: string;
  title: string;
  description: string;
  h1: string;
  lead: string;
  capsule: string | null;
  blocks: TextBlock[];
  faq: FaqItem[];
}

const FILES = import.meta.glob<TextPage>('../data/pages/*/*.json', { eager: true, import: 'default' });

export const TEXT_PAGES: readonly TextPage[] = Object.values(FILES);

const BY_URL = new Map(TEXT_PAGES.map((page) => [page.url, page]));

/** The ten service pages of spec stage 6 §6 (their `page_id`s). */
export const SERVICE_PAGE_IDS: ReadonlySet<string> = new Set([
  'about', 'contact', 'how-readings-work', 'privacy', 'terms',
  'sobre-nosotros', 'contacto', 'como-funcionan-las-lecturas', 'privacidad', 'terminos',
]);

export function textPage(path: string): TextPage {
  const page = BY_URL.get(path);
  if (!page) throw new Error(`no text page for ${path} in src/data/pages`);
  return page;
}

/** Every string of a page the reader sees. */
export function pageTexts(page: TextPage): string[] {
  return [page.title, page.description, page.h1, page.lead, page.capsule ?? '',
    ...page.blocks.flatMap((b) => [b.heading, ...b.paragraphs]), ...page.faq.flatMap((f) => [f.q, f.a])];
}

export function isHidden(page: TextPage, facts: Facts = FACTS): boolean {
  const missing = missingFacts(pageTexts(page), facts);
  if (missing.length === 0) return false;
  if (SERVICE_PAGE_IDS.has(page.page_id)) return true;
  throw new Error(`${page.url}: no value for {${missing.join('}, {')}} in src/data/facts.json`);
}

export function filledPage(page: TextPage, facts: Facts = FACTS): TextPage {
  const f = (text: string) => fillFacts(text, facts);
  return {
    ...page,
    title: f(page.title), description: f(page.description), h1: f(page.h1), lead: f(page.lead),
    capsule: page.capsule === null ? null : f(page.capsule),
    blocks: page.blocks.map((b) => ({ ...b, heading: f(b.heading), paragraphs: b.paragraphs.map(f) })),
    faq: page.faq.map((item) => ({ q: f(item.q), a: f(item.a) })),
  };
}

export function hiddenPaths(facts: Facts = FACTS): Set<string> {
  return new Set(TEXT_PAGES.filter((page) => isHidden(page, facts)).map((page) => page.url));
}

/** The address of a page, or null while it is hidden: links to it appear together with the page (spec stage 6 §6). */
export function openPagePath(key: PageKey, lang: Lang, hidden: ReadonlySet<string> = hiddenPaths()): string | null {
  const path = pagePath(key, lang);
  return hidden.has(path) ? null : path;
}
