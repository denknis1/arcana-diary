import { describe, expect, it } from 'vitest';
import { alternates } from './seo';
import { indexablePaths, sitemapXml } from './sitemap';

describe('sitemap (spec stage 6 §3)', () => {
  it('lists the indexable pages: no diary, no account, no 404, no hidden service page', () => {
    const paths = indexablePaths();
    expect(paths).toHaveLength(187 - 4 - 2 - 8); // no diary/account, no 404, no hidden service page
    expect(paths).toContain('/how-readings-work');
    expect(paths).toContain('/cards');
    expect(paths).toContain('/es/tiradas/3-cartas');
    for (const p of ['/diary', '/es/diario', '/account', '/es/cuenta', '/404', '/es/404', '/about']) {
      expect(paths).not.toContain(p);
    }
  });

  it('writes plain addresses: hreflang lives only in the page head (stage 2 spec §3: one method)', () => {
    expect(sitemapXml(['/', '/one-card'])).toBe('<?xml version="1.0" encoding="UTF-8"?>\n'
      + '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
      + '<url><loc>https://arcanadiary.com/</loc></url>\n'
      + '<url><loc>https://arcanadiary.com/one-card</loc></url>\n'
      + '</urlset>\n');
  });

  it('pairs an indexable page only with an indexable page', () => {
    const indexable = new Set(indexablePaths().map((p) => `https://arcanadiary.com${p}`));
    for (const path of indexablePaths()) {
      for (const a of alternates(path)) expect(indexable, `${path} → ${a.href}`).toContain(a.href);
    }
  });
});
