import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Issue #1191: /stats used to pass the entire tribunal_calendar contract
 * (~13.9MB, every tribunal x date in the archive) as a `calendarRows` prop
 * to TribunalCoverageExplorer, a `client:only="svelte"` island. client:only
 * still serializes its props into the page for hydration, so that shipped
 * the whole archive to every /stats visitor even though the drill-down UI
 * only ever renders one tribunal's days at a time.
 *
 * This is a structural gate, not a byte-budget assertion: it fails the
 * moment either half of the fix regresses — the component re-declaring a
 * bulk rows prop, or the page re-wiring it — well before anyone would need
 * to notice a payload size regression by hand.
 */

const componentPath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  'TribunalCoverageExplorer.svelte',
);
const statsPagePath = resolve(
  dirname(fileURLToPath(import.meta.url)),
  '..',
  'pages',
  'stats.astro',
);

describe('stats.astro payload budget (issue #1191)', () => {
  it('TribunalCoverageExplorer no longer declares a bulk calendarRows prop', () => {
    const source = readFileSync(componentPath, 'utf-8');
    expect(source).not.toMatch(/calendarRows/);
  });

  it('TribunalCoverageExplorer loads data by fetching a per-tribunal partition', () => {
    const source = readFileSync(componentPath, 'utf-8');
    expect(source).toMatch(/loadTribunalCalendarPartition/);
  });

  it('stats.astro never passes the full tribunal_calendar array as an island prop', () => {
    const source = readFileSync(statsPagePath, 'utf-8');
    expect(source).not.toMatch(/calendarRows=\{/);
  });
});
