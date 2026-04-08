import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  prefetch: true,
  site: 'https://franklinbaldo.github.io',
  base: '/causaganha',
  integrations: [svelte()],
  vite: {
    plugins: [tailwindcss()],
  },
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
