import { describe, expect, it } from 'vitest';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * The Cobogó/Panda reboot (#1169) deleted `styles/base.css` — which defined
 * `.auto-grid`/`.auto-grid-sm` (an equal-column grid that collapses to one
 * column on narrow screens) — and dropped the `@picocss/pico` import that
 * gave bare `.grid` its native semantic-grid behavior. Neither utility was
 * migrated into the new `index.css` bridge, but at least eight Svelte/Astro
 * components kept using the class names in markup, so those wrappers have
 * rendered as plain block/flow stacks with no grid layout ever since,
 * regardless of viewport. This is the same "migration removes the system
 * but not every reference to it" pattern already caught once for
 * `--pico-muted-border-color` (PR #1309) and the whole Pico CSS section of
 * FRONTEND.md (PR #1311) — here it is live layout CSS, not just prose.
 *
 * `.grid` itself is Pico-specific naming this project no longer uses
 * anywhere else (CLAUDE.md: "`--pico-*` ... no longer exist anywhere in the
 * codebase") — its one remaining call site is migrated to `.auto-grid`
 * rather than reintroducing a Pico-named utility.
 */

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const indexCss = readFileSync(join(srcRoot, 'index.css'), 'utf-8');

function listSourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      out.push(...listSourceFiles(full));
    } else if (/\.(astro|svelte)$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

describe('auto-grid CSS bridge (orphaned by the Cobogó/Panda reboot, #1169)', () => {
  it('defines .auto-grid and .auto-grid-sm in the global CSS bridge', () => {
    expect(indexCss).toMatch(/\.auto-grid\s*\{/);
    expect(indexCss).toMatch(/\.auto-grid-sm\s*\{/);
  });

  it('has no source file using the removed Pico .grid utility class', () => {
    const offenders: string[] = [];
    for (const file of listSourceFiles(srcRoot)) {
      const contents = readFileSync(file, 'utf-8');
      if (/class="grid"/.test(contents) || /class='grid'/.test(contents)) {
        offenders.push(file);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('every component referencing auto-grid/auto-grid-sm can rely on a real definition', () => {
    const consumers: string[] = [];
    for (const file of listSourceFiles(srcRoot)) {
      const contents = readFileSync(file, 'utf-8');
      if (/class="[^"]*\bauto-grid(-sm)?\b/.test(contents)) {
        consumers.push(file);
      }
    }
    // Sanity check the scan itself still finds the known consumers, so this
    // test cannot pass vacuously if the scan logic regresses.
    expect(consumers.length).toBeGreaterThan(0);
  });
});
