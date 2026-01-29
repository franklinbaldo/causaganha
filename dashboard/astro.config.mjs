import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
    site: 'https://franklinbaldo.github.io',
    base: '/causaganha',
    integrations: [
        react(),
        tailwind()
    ],
    output: 'static'
});
