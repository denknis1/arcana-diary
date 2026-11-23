// sitemap.xml by our own code at build time (spec stage 6 §3, no new packages): every indexable page as a plain
// <url><loc>; hreflang lives only in the page head (stage 2 spec §3: one method). The diary, the account, the 404
// pages and the hidden service pages stay out.
import { PRIVATE_PAIRS, allPagePaths } from './routes';
import { absoluteUrl } from './seo';
import { hiddenPaths } from './textPages';

export function indexablePaths(): string[] {
  const hidden = hiddenPaths();
  return allPagePaths().filter((p) => !(p in PRIVATE_PAIRS) && !p.endsWith('/404') && !hidden.has(p));
}

const escape = (text: string) => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function sitemapXml(paths: readonly string[]): string {
  const urls = paths.map((path) => `<url><loc>${escape(absoluteUrl(path))}</loc></url>`);
  return '<?xml version="1.0" encoding="UTF-8"?>\n'
    + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + `${urls.join('\n')}\n</urlset>\n`;
}
