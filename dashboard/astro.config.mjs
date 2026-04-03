import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

// https://astro.build/config
export default defineConfig({
  prefetch: true,
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [preact({ compat: true })],
  output: 'static',
  trailingSlash: 'never',
  prefetch: {
    defaultStrategy: 'hover',
  },
  build: {
    assets: '_astro',
    format: 'file',
  },
});
