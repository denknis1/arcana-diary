// /data/daily-en.json, /data/daily-es.json: upright meanings of the 78 cards, fetched by the Card of the Day only
// when GET /api/daily answers 503 (src/lib/daily.ts).
import en from '../../data/meanings.en.json';
import es from '../../data/meanings.es.json';

export function getStaticPaths() {
  return [{ params: { lang: 'en' } }, { params: { lang: 'es' } }];
}

export function GET({ params }: { params: { lang: 'en' | 'es' } }) {
  const meanings = params.lang === 'es' ? es : en;
  return new Response(JSON.stringify(meanings.map((m) => ({ card_id: m.card_id, upright: m.upright }))), {
    headers: { 'content-type': 'application/json' },
  });
}
