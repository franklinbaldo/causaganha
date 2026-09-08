import { describe, expect, it } from 'vitest';
import * as coverageInsights from './coverageInsights';
import { buildTribunalAttentionCards } from './coverageInsights';

describe('coverageInsights module surface', () => {
  it('exposes only the tribunal-detail helper actually used by a page or component', () => {
    // summarizeCatalogDay/filterCoverageDays/countCoverageFilters/getDayStatusLabel/
    // buildCatalogAttentionCards had zero callers anywhere in web/src -- including the
    // calendar-day (not business-day) 'recent-drop'/'persistent-absence' heuristics inside
    // buildCatalogAttentionCards that a prior loop round flagged but could not confirm live.
    // This guard keeps that dead surface from silently reappearing.
    expect(Object.keys(coverageInsights).sort()).toEqual(['buildTribunalAttentionCards']);
  });
});

describe('buildTribunalAttentionCards', () => {
  it('does not flag a fully-resolved tribunal as an anomaly just because it has legitimate absent days', () => {
    // A tribunal with 0 missing days (fully caught up) but a normal share of
    // legitimately-absent days (weekends/holidays) — nothing left to collect.
    const expectedDays = 100;
    const absentCount = 15;
    const coverageSize = expectedDays - absentCount; // 85, so missingDays === 0
    const completionPct = ((coverageSize + absentCount) / expectedDays) * 100; // 100

    const cards = buildTribunalAttentionCards({
      tribunal: 'TJRO',
      missingDays: 0,
      absentCount,
      expectedDays,
      coverageSize,
      completionPct,
    });

    expect(cards.find(c => c.id === 'tribunal-anomaly')).toBeUndefined();
  });

  it('still flags a genuinely low-completion tribunal as an anomaly', () => {
    const expectedDays = 100;
    const absentCount = 5;
    const coverageSize = 40; // completion = (40 + 5) / 100 = 45%
    const completionPct = ((coverageSize + absentCount) / expectedDays) * 100;

    const cards = buildTribunalAttentionCards({
      tribunal: 'TJRO',
      missingDays: 55,
      absentCount,
      expectedDays,
      coverageSize,
      completionPct,
    });

    const anomaly = cards.find(c => c.id === 'tribunal-anomaly');
    expect(anomaly).toBeDefined();
    expect(anomaly?.summary).toContain('45.0%');
  });
});
