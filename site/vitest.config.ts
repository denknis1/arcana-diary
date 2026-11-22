import { defineConfig } from 'vitest/config';

// Logic without a screen lives in src/lib and src/i18n and is tested here in Node. Screens (spec 4.4b §9, §11) are
// tested in *.test.tsx files that start with `// @vitest-environment happy-dom` (a DOM in memory, no browser, no
// network: fetch is replaced in every test). TZ is fixed, so a date a test names never depends on the machine; the
// day rules themselves are tested with local dates (spec 4.4b §2, decision 13).
export default defineConfig({
  esbuild: { jsx: 'automatic', jsxImportSource: 'preact' },
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    environment: 'node',
    environmentOptions: { happyDOM: { url: 'https://arcana.test/' } },
    env: { TZ: 'UTC' },
  },
});
