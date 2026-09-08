import { describe, expect, it } from 'vitest';
import { calculateVelocityAndRegression } from './velocityCalc';

/**
 * SyncManifest.build() (src/djen_backup/manifest.py) only ever creates
 * (tribunal, date) rows for weekdays -- weekends never exist in the
 * manifest, so a fully-collected tribunal can never have weekend dates in
 * its coverage set. `calculateVelocityAndRegression` must size its coverage
 * denominators (current30Days/baseline60Days) by business days, not by raw
 * calendar days, or a fully-caught-up tribunal is permanently reported as
 * ~71% covered (5/7).
 */
function businessDaysCollectedSince(startIso: string, endIso: string): Set<string> {
  const collected = new Set<string>();
  const cur = new Date(startIso + 'T00:00:00Z');
  const end = new Date(endIso + 'T00:00:00Z');
  while (cur <= end) {
    const day = cur.getUTCDay();
    if (day !== 0 && day !== 6) collected.add(cur.toISOString().split('T')[0]);
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  return collected;
}

describe('calculateVelocityAndRegression', () => {
  it('reports ~100% current and baseline coverage when every business day since start was collected', () => {
    const start = '2025-09-01'; // Monday, > 90 days before the target end below
    const end = '2026-01-16'; // Friday
    const coverageSet = businessDaysCollectedSince(start, end);

    const result = calculateVelocityAndRegression(coverageSet, end, start);

    expect(result).not.toBeNull();
    expect(result!.currentCoverage).toBeGreaterThan(99);
    expect(result!.baselineCoverage).toBeGreaterThan(99);
  });

  it('still reports partial coverage proportionally when some business days are missing', () => {
    const start = '2025-09-01';
    const end = '2026-01-16';
    const fullyCollected = businessDaysCollectedSince(start, end);
    // Drop every other business day from the most recent 30-day window only.
    const cutoff = new Date(end + 'T00:00:00Z');
    cutoff.setUTCDate(cutoff.getUTCDate() - 29);
    const cutoffIso = cutoff.toISOString().split('T')[0];
    const coverageSet = new Set(
      [...fullyCollected].filter((d, idx) => d < cutoffIso || idx % 2 === 0)
    );

    const result = calculateVelocityAndRegression(coverageSet, end, start);

    expect(result).not.toBeNull();
    expect(result!.currentCoverage).toBeLessThan(90);
    expect(result!.baselineCoverage).toBeGreaterThan(99);
  });
});
