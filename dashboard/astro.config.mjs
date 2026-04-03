import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  prefetch: true,
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [
    preact({ compat: true }),
    tailwind({
      applyBaseStyles: false, // Keep custom index.css
    }),
  ],
  output: 'static',
  trailingSlash: 'never',
  build: {
    assets: '_astro',
    format: 'file',
  },
});
