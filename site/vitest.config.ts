import { defineConfig } from 'vitest/config';

// Logic without a screen lives in src/lib and src/i18n and is tested here in Node; islands stay thin.
export default defineConfig({
  test: { include: ['src/**/*.test.ts'], environment: 'node' },
});
