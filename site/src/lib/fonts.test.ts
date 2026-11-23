import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

// Spec 4.9 §1 item 4: the fonts come from our own server; no page asks Google for them.
const css = readFileSync('src/styles/global.css', 'utf8');
const base = readFileSync('src/layouts/Base.astro', 'utf8');

function htmlFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? htmlFiles(join(dir, e.name)) : e.name.endsWith('.html') ? [join(dir, e.name)] : []);
}

describe('own fonts', () => {
  it('the layout has no reference to Google Fonts', () => {
    expect(base).not.toMatch(/fonts\.g(oogleapis|static)/);
  });

  it('@font-face covers both families, latin and latin-ext, and every file exists', () => {
    const files = [...css.matchAll(/url\('\/fonts\/([^']+\.woff2)'\)/g)].map((m) => m[1]);
    expect(files.sort()).toEqual(['cormorant-garamond-latin-ext.woff2', 'cormorant-garamond-latin.woff2',
      'manrope-latin-ext.woff2', 'manrope-latin.woff2']);
    for (const f of files) expect(existsSync(`public/fonts/${f}`), f).toBe(true);
    expect(css).toContain('font-weight: 500 600');
    expect(css).toContain('font-weight: 400 700');
    expect(css).not.toMatch(/fonts\.g(oogleapis|static)/);
  });

  it.runIf(existsSync('dist'))('the built site has no external font reference', () => {
    for (const file of htmlFiles('dist')) expect(readFileSync(file, 'utf8'), file).not.toContain('fonts.g');
  });
});
