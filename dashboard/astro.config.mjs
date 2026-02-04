import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';

// https://astro.build/config
export default defineConfig({
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [
    react(),
    tailwind({
      applyBaseStyles: false, // Keep custom index.css
    }),
  ],
  output: 'static',
  build: {
    assets: '_astro',
  },
});
