import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));

// advogados.astro and comparador.astro are trivial redirect stubs to /stats
// (CLAUDE.md's CSS token boundary section names them as the only two
// holdout pages). Both already redirect via <meta http-equiv="refresh">;
// the <script define:vars> that duplicated the redirect in JS was the only
// inline script anywhere in the app and would have required 'unsafe-inline'
// in Layout.astro's script-src (#1613, TM-08). Removed as dead weight,
// guarded here so it doesn't come back.
const STUB_PAGES = ['advogados.astro', 'comparador.astro'];

describe('redirect stub pages carry no inline <script> (#1613, TM-08)', () => {
  for (const page of STUB_PAGES) {
    it(`${page} has no inline <script> tag (meta refresh already redirects)`, () => {
      const source = readFileSync(resolve(__dirname, page), 'utf-8');
      expect(source).not.toMatch(/<script/);
      expect(source).toMatch(/<meta http-equiv="refresh"/);
    });
  }
});
