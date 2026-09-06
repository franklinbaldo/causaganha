import { describe, expect, it } from 'vitest';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

/**
 * Issue #1178: the Cobogó/Panda reboot (#1169) deleted `PageHeader.astro`,
 * the only renderer of `ThemeToggle.astro`, and dropped the theme
 * pre-paint script — but left `ThemeToggle.astro` itself orphaned in the
 * tree, still referencing CSS custom properties that no longer exist
 * anywhere in the Cobogó/Panda foundation.
 *
 * Investigation for #1178 found the shared `cobogo` preset
 * (node_modules/cobogo/preset/index.mjs) defines no dark-mode
 * semantic-token variant, no Panda conditions, and no `data-theme`
 * awareness at all — it is a single, flat light palette. Restoring the
 * toggle would mean building a second, project-local theming system next
 * to Cobogó, which the project's own skill guidance
 * (node_modules/cobogo/skills/cobogo/SKILL.md) says to avoid. The decision
 * (AgentDecision, this round) is therefore single-theme: CausaGanha does
 * not offer a light/dark toggle, and the dead component is removed rather
 * than kept as an inert, half-wired feature.
 *
 * This test is the gate against that dead code silently reappearing.
 */

const srcRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const LEGACY_THEME_MARKERS = [
  'data-theme',
  'causaganha-theme',
  '--font-size-sm',
  '--radius-btn',
  '--transition-base',
  '--color-base-200',
];

function listSourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      out.push(...listSourceFiles(full));
    } else if (/\.(astro|svelte|ts|tsx|css)$/.test(entry) && !entry.endsWith('.test.ts')) {
      out.push(full);
    }
  }
  return out;
}

describe('single-theme decision (issue #1178)', () => {
  it('does not ship an orphaned ThemeToggle component', () => {
    expect(existsSync(join(srcRoot, 'components', 'ThemeToggle.astro'))).toBe(false);
  });

  it('has no source file referencing the removed light/dark theming plumbing', () => {
    const offenders: string[] = [];
    for (const file of listSourceFiles(srcRoot)) {
      const contents = readFileSync(file, 'utf-8');
      for (const marker of LEGACY_THEME_MARKERS) {
        if (contents.includes(marker)) {
          offenders.push(`${file} references "${marker}"`);
        }
      }
    }
    expect(offenders).toEqual([]);
  });
});
