import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';

// https://astro.build/config
export default defineConfig({
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [svelte()],
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
