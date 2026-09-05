import { defineConfig } from '@pandacss/dev';
import cobogo from 'cobogo/preset';

export default defineConfig({
  preflight: true,
  include: ['./src/**/*.{astro,js,jsx,ts,tsx,svelte}'],
  exclude: ['./node_modules/**', './dist/**'],
  presets: [cobogo],
  outdir: 'styled-system',
});
