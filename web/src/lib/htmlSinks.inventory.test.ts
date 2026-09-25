import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const srcRoot = resolve(__dirname, '..');

// The only two sinks reviewed and authorized to render sanitized judicial
// text as HTML (see web/src/lib/djen.ts's sanitizeHtml + CLAUDE.md's DOMPurify
// note and docs/SECURITY_THREAT_MODEL.md TM-08). Any other {@html} usage is
// an unreviewed sink and must fail this test until it is either removed or
// added to this list alongside a review of what it renders.
const AUTHORIZED_HTML_SINKS = [
  'components/PublicationDetailPanel.svelte',
  'components/PublicationReader.svelte',
];

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (entry.isFile() && (entry.name.endsWith('.svelte') || entry.name.endsWith('.astro'))) {
      out.push(full);
    }
  }
  return out;
}

describe('{@html} sink inventory (#1613, TM-08)', () => {
  it('only the reviewed sanitized-text sinks use {@html}', () => {
    const files = walk(srcRoot);
    const sinkFiles = files
      .filter((f) => readFileSync(f, 'utf-8').includes('{@html'))
      .map((f) => f.slice(srcRoot.length + 1).replace(/\\/g, '/'))
      .sort();

    expect(sinkFiles).toEqual([...AUTHORIZED_HTML_SINKS].sort());
  });

  it('each authorized sink only renders textoRender.content (the sanitizeHtml output), never a raw field', () => {
    for (const relPath of AUTHORIZED_HTML_SINKS) {
      const source = readFileSync(join(srcRoot, relPath), 'utf-8');
      const htmlLine = source
        .split('\n')
        .find((line) => line.includes('{@html'));
      expect(htmlLine, `${relPath} should contain an {@html} line`).toBeDefined();
      expect(htmlLine).toMatch(/textoRender\.content/);
    }
  });
});
