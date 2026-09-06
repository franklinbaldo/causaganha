// @vitest-environment node
//
// vitePreprocess() shells out to esbuild, which asserts
// `new TextEncoder().encode('') instanceof Uint8Array` — jsdom's TextEncoder
// fails that invariant, so this file must run under the real Node environment.
import { readFileSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { vitePreprocess } from '@astrojs/svelte';
import { compile, preprocess } from 'svelte/compiler';
import { describe, expect, it } from 'vitest';

const componentsDir = path.dirname(fileURLToPath(import.meta.url));

async function listSvelteFiles(dir: string): Promise<string[]> {
  const entries = await readdir(dir, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((entry) => {
      const entryPath = path.join(dir, entry.name);
      if (entry.isDirectory()) return listSvelteFiles(entryPath);
      return entry.name.endsWith('.svelte') ? [entryPath] : [];
    })
  );
  return files.flat();
}

describe('every Svelte component compiles with zero accessibility warnings', () => {
  it('has no a11y_* compiler warnings (e.g. a noninteractive element with a tabindex)', async () => {
    const srcRoot = path.resolve(componentsDir, '..');
    const files = await listSvelteFiles(srcRoot);
    expect(files.length).toBeGreaterThan(0);

    const a11yWarnings: string[] = [];
    for (const file of files) {
      const relative = path.relative(srcRoot, file);
      const source = readFileSync(file, 'utf8');
      const processed = await preprocess(source, vitePreprocess(), { filename: relative });
      const { warnings } = compile(processed.code, { filename: relative });
      for (const warning of warnings) {
        if (!warning.code.startsWith('a11y_')) continue;
        a11yWarnings.push(`${relative}: [${warning.code}] ${warning.message}`);
      }
    }

    expect(a11yWarnings).toEqual([]);
  });
});
