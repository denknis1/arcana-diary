import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// Addresses without a trailing slash (/one-card, /es/si-o-no): one HTML file per page, served by Caddy with
// try_files {path} {path}.html (deploy/Caddyfile).
export default defineConfig({
  site: 'https://arcanadiary.com',
  output: 'static',
  trailingSlash: 'never',
  build: { format: 'file' },
  integrations: [preact()],
});
