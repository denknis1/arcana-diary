// /sitemap.xml (spec stage 6 §3): written once at build time.
import { indexablePaths, sitemapXml } from '../lib/sitemap';

export function GET() {
  return new Response(sitemapXml(indexablePaths()), { headers: { 'content-type': 'application/xml; charset=utf-8' } });
}
