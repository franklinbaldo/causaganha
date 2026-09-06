import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const layoutSource = readFileSync(resolve(__dirname, 'Layout.astro'), 'utf-8');

function extractBetween(source: string, startTag: string, endTag: string): string {
  const start = source.indexOf(startTag);
  const end = source.indexOf(endTag, start);
  if (start === -1 || end === -1) throw new Error(`Could not find ${startTag}..${endTag} in Layout.astro`);
  return source.slice(start, end);
}

describe('Agentes discovery in the site header/footer (#1219)', () => {
  it('lists Agentes in the always-visible primary nav, not only inside the "Mais" menu', () => {
    const detailsBlock = extractBetween(layoutSource, '<details', '</details>');
    const outsideDetails = layoutSource.replace(detailsBlock, '');
    expect(outsideDetails).toMatch(/label:\s*'Agentes'/);
    expect(outsideDetails).toMatch(/match:\s*'\/agentes'/);
  });

  it('does not duplicate the Agentes link inside the "Mais" menu once it is promoted', () => {
    const detailsBlock = extractBetween(layoutSource, '<details', '</details>');
    expect(detailsBlock).not.toMatch(/agentes/i);
  });

  it('links to /agentes from the public footer', () => {
    const footerBlock = extractBetween(layoutSource, '<footer', '</footer>');
    expect(footerBlock).toMatch(/BASE \+ 'agentes'/);
    expect(footerBlock).toMatch(/Agentes/);
  });
});
