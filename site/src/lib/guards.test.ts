// Rules for every source file of the site (00-design.md "Правила для кода", spec 4.4a §4, §7).
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { extname, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

// Resolved from this file, not from the working directory.
const SRC = fileURLToPath(new URL('..', import.meta.url));
const ROOT = join(SRC, '..');

const CODE_EXT = new Set(['.ts', '.tsx', '.astro', '.css', '.mjs', '.js', '.jsx', '.mts', '.cts', '.html', '.md', '.mdx', '.svelte', '.vue']);
const DATA_EXT = new Set(['.json', '.svg', '.png', '.webp', '.jpg', '.jpeg', '.avif', '.gif', '.ico', '.woff2', '.txt']);
const TEXT_DATA_EXT = new Set(['.json', '.svg', '.txt']);

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : [path];
  });
}

const rel = (p: string) => relative(SRC, p).split(sep).join('/');
const read = (p: string) => readFileSync(p, 'utf-8');
const isTest = (p: string) => /\.test\.tsx?$/.test(p);
const isHelper = (p: string) => rel(p).split('/').includes('testing');

const ALL = files(SRC);
const CODE = ALL.filter((p) => CODE_EXT.has(extname(p).toLowerCase()));
// Test files and testing/ helpers legitimately contain the forbidden words.
const SOURCES = CODE.filter((p) => !isTest(p) && !isHelper(p));
const DATA_TEXT = ALL.filter((p) => TEXT_DATA_EXT.has(extname(p).toLowerCase()));

describe('site sources', () => {
  it('scan a real set of files, nothing unknown', () => {
    expect(SOURCES.length).toBeGreaterThan(20);
    expect(SOURCES.map(rel)).toContain('lib/turnstile.ts');
    const unknown = ALL.filter((p) => {
      const ext = extname(p).toLowerCase();
      return !CODE_EXT.has(ext) && !DATA_EXT.has(ext);
    });
    expect(unknown.map(rel)).toEqual([]);
  });

  it('never import from a test file in production code', () => {
    for (const path of SOURCES) {
      expect(read(path), rel(path)).not.toMatch(/(?:from\s*|import\s*\(?\s*|require\s*\(\s*)['"][^'"]*\.test(?:\.[a-z]+)?['"]/);
    }
  });

  it('never put text in as markup (one exception: the JSON-LD script, escaped by ldScript)', () => {
    const sink = /innerHTML|dangerouslySetInnerHTML|set:html|insertAdjacentHTML|outerHTML\s*=|document\.write|createContextualFragment|srcdoc|new Function\(|\beval\(/;
    const allowed = (path: string) => (rel(path) === 'components/JsonLd.astro'
      ? read(path).replace('set:html={ldScript(data)}', '') : read(path));
    for (const path of SOURCES) expect(allowed(path), rel(path)).not.toMatch(sink);
    expect(read(join(SRC, 'components/JsonLd.astro'))).toContain('set:html={ldScript(data)}');
  });

  it('take colours only from the tokens', () => {
    const colour = /#[0-9a-f]{3,8}\b(?![\w-])|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/i;
    for (const path of SOURCES.filter((p) => rel(p) !== 'styles/tokens.css')) {
      expect(read(path), rel(path)).not.toMatch(colour);
    }
  });

  it('hold no secrets and no key of their own', () => {
    const secret = /sk-ant|sk_live|sk_test|sb_secret|TURNSTILE_SECRET|SUPABASE_SERVICE|service_role|0x4AAAA|ANTHROPIC_API_KEY|eyJ[A-Za-z0-9_-]{10,}\./;
    const env = /import\.meta\.env(?!\.(?:PUBLIC_|MODE\b|DEV\b|PROD\b|BASE_URL\b|SSR\b|SITE\b))/;
    for (const path of [...SOURCES, ...DATA_TEXT, join(ROOT, 'astro.config.mjs'), join(ROOT, 'package.json')]) {
      expect(read(path), path).not.toMatch(secret);
    }
    for (const path of SOURCES) expect(read(path), rel(path)).not.toMatch(env);
  });

  it('read streams with fetch, never EventSource', () => {
    // Whole-line comments may name it (sse.ts explains why it is not used); any code mention fails.
    const code = (p: string) => read(p).split('\n').filter((l) => !/^\s*(?:\/\/|\/?\*)/.test(l)).join('\n');
    for (const path of SOURCES) expect(code(path), rel(path)).not.toMatch(/\bEventSource\b/);
  });

  it('import @supabase/auth-js only in src/lib/supabaseClient.ts (spec 4.4b §3: a chunk of its own)', () => {
    const users = SOURCES.filter((p) => /from\s*['"]@supabase\/|import\(\s*['"]@supabase\//.test(read(p)));
    expect(users.map(rel)).toEqual(['lib/supabaseClient.ts']);
  });

  it('load supabaseClient.ts only with import(), only from src/lib/auth.ts', () => {
    const users = SOURCES.filter((p) => /['"]\.{1,2}\/(?:[\w/]*\/)?supabaseClient['"]/.test(read(p)));
    expect(users.map(rel)).toEqual(['lib/auth.ts']);
    expect(read(join(SRC, 'lib/auth.ts'))).toMatch(/import\(\s*['"]\.\/supabaseClient['"]\s*\)/);
    expect(read(join(SRC, 'lib/auth.ts'))).not.toMatch(/from\s*['"]\.\/supabaseClient['"]/);
  });

  it('load the Turnstile script only from src/lib/turnstile.ts', () => {
    const users = SOURCES.filter((p) => /challenges\.cloudflare\.com|turnstile\/v0|cloudflare\.com\/turnstile/.test(read(p)));
    expect(users.map(rel)).toEqual(['lib/turnstile.ts']);
  });
});
