import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [
    preact({ compat: true }),
    tailwind({
      applyBaseStyles: false, // Keep custom index.css
    }),
  ],
  output: 'static',
  build: {
    assets: '_astro',
  },
});
