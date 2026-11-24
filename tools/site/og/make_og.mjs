// Share image (1200×630, EN/ES) and site icons from the moon mark — stage 7.2.
// Run from the repo root (Node only in Docker; sharp from site/node_modules; TTF fonts from tools/site/og/fonts):
//   docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/repo" -v "$PWD/tools/site/og/fonts:/usr/share/fonts/og:ro" \
//     -w /repo node:22 node tools/site/og/make_og.mjs
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import sharp from '/repo/site/node_modules/sharp/lib/index.js';

const OUT = '/repo/site/public';
const NIGHT = '#10163A', GOLD = '#C9A45C', CREAM = '#F1ECE2', MIST = '#D8CFE4';
const MOON = (s) => `<circle cx="32" cy="32" r="30" stroke="${GOLD}" stroke-width="${2.5 * s}" fill="none"/>`
  + `<path d="M39 14a19 19 0 1 0 0 36A15 15 0 1 1 39 14Z" stroke="${GOLD}" stroke-width="${3 * s}" fill="none"/>`;

async function cardPng(slug) {
  const buf = await sharp(`${OUT}/cards/${slug}@350.webp`).png().toBuffer();
  return `data:image/png;base64,${buf.toString('base64')}`;
}

const esc = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;');

async function og(lang, lines, chips) {
  const [star, moon, sun] = await Promise.all(['the-star', 'the-moon', 'the-sun'].map(cardPng));
  let x = 84;
  const chipSvg = chips.map((c) => {
    const w = Math.round(c.length * 11.2 + 40);
    const s = `<rect x="${x}" y="440" width="${w}" height="44" rx="22" fill="none" stroke="${GOLD}"/>`
      + `<text x="${x + w / 2}" y="469" text-anchor="middle" font-family="Manrope" font-weight="600" font-size="20" fill="${GOLD}">${esc(c)}</text>`;
    x += w + 12;
    return s;
  }).join('');
  const card = (href, cx, w, y) => {
    const h = Math.round(w * 12 / 7);
    return `<rect x="${cx - 3}" y="${y - 3}" width="${w + 6}" height="${h + 6}" rx="11" fill="${GOLD}"/>`
      + `<image href="${href}" x="${cx}" y="${y}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid slice"/>`;
  };
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
<rect width="1200" height="630" fill="${NIGHT}"/>
<rect x="24" y="24" width="1152" height="582" rx="20" fill="none" stroke="${GOLD}" stroke-opacity="0.45"/>
<g transform="translate(84,128) scale(1.25)">${MOON(1)}</g>
<text x="182" y="190" font-family="Cormorant Garamond" font-weight="600" font-size="84" fill="${CREAM}">Arcana Diary</text>
${lines.map((l, i) => `<text x="84" y="${282 + i * 44}" font-family="Manrope" font-weight="500" font-size="31" fill="${MIST}">${esc(l)}</text>`).join('\n')}
${chipSvg}
${card(star, 742, 120, 210)}${card(sun, 1032, 120, 210)}${card(moon, 878, 136, 182)}
</svg>`;
  mkdirSync(`${OUT}/og`, { recursive: true });
  await sharp(Buffer.from(svg)).jpeg({ quality: 88, mozjpeg: true }).toFile(`${OUT}/og/og-${lang}.jpg`);
}

async function icons() {
  const svg = (pad) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">`
    + `<rect width="64" height="64" rx="${pad ? 14 : 12}" fill="${NIGHT}"/>`
    + `<g transform="translate(${pad ? 10 : 6},${pad ? 10 : 6}) scale(${pad ? 0.6875 : 0.8125})">${MOON(1.15)}</g></svg>`;
  writeFileSync(`${OUT}/favicon.svg`, svg(false));
  await sharp(Buffer.from(svg(false))).resize(32, 32).png().toFile(`${OUT}/favicon-32.png`);
  await sharp(Buffer.from(svg(true))).resize(180, 180).png().toFile(`${OUT}/apple-touch-icon.png`);
  await sharp(Buffer.from(svg(true))).resize(192, 192).png().toFile(`${OUT}/icon-192.png`);
  await sharp(Buffer.from(svg(true))).resize(512, 512).png().toFile(`${OUT}/icon-512.png`);
  writeFileSync(`${OUT}/site.webmanifest`, JSON.stringify({
    name: 'Arcana Diary', short_name: 'Arcana Diary', start_url: '/', display: 'browser',
    background_color: '#F7F2EC', theme_color: NIGHT,
    icons: [{ src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png' }],
  }, null, 2) + '\n');
}

await og('en', ['Ask your question and draw the cards.', 'An AI reader explains them in plain words.'],
  ['Free tarot reading', 'Yes or no', '78 card meanings']);
await og('es', ['Haz tu pregunta y saca las cartas.', 'Una lectura con IA en palabras sencillas.'],
  ['Tarot gratis', 'Sí o no', 'Las 78 cartas']);
await icons();
console.log('ok');
