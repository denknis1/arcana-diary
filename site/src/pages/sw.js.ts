// /sw.js (stage 8.1 §4): the service worker of the morning reminder, written once at build time (src/lib/sw.ts).
import { swSource, swTexts } from '../lib/sw';

export function GET() {
  return new Response(swSource(swTexts()), { headers: { 'content-type': 'application/javascript; charset=utf-8' } });
}
