// Rules for every source file of the site (00-design.md "Правила для кода", spec 4.4a §4, §7).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

const SOURCES = files('src').filter((p) => /\.(ts|tsx|astro|css|mjs)$/.test(p) && !p.endsWith('.test.ts') && !p.includes('/testing/'));
const read = (p: string) => readFileSync(p, 'utf-8');

describe('site sources', () => {
  it('never put text in as markup', () => {
    for (const path of SOURCES) expect(read(path), path).not.toMatch(/innerHTML|dangerouslySetInnerHTML|set:html|insertAdjacentHTML|outerHTML/);
  });

  it('take colours only from the tokens', () => {
    for (const path of SOURCES.filter((p) => !p.endsWith('tokens.css'))) {
      expect(read(path), path).not.toMatch(/#[0-9a-fA-F]{3,8}\b(?![\w-])|rgba?\(|hsla?\(/);
    }
  });

  it('hold no secrets and no key of their own', () => {
    for (const path of [...SOURCES, 'astro.config.mjs', 'package.json']) {
      expect(read(path), path).not.toMatch(/sk-ant|TURNSTILE_SECRET|SUPABASE_SERVICE|service_role|0x4AAAA|ANTHROPIC_API_KEY/);
    }
  });

  it('read streams with fetch, never EventSource', () => {
    for (const path of SOURCES) expect(read(path), path).not.toMatch(/new EventSource/);
  });

  it('load the Turnstile script only from src/lib/turnstile.ts', () => {
    const users = SOURCES.filter((p) => read(p).includes('challenges.cloudflare.com'));
    expect(users).toEqual([join('src', 'lib', 'turnstile.ts')]);
  });
});
