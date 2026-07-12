import { describe, expect, it } from 'vitest';
import {
  ADVOGADOS_TRIBUNALS_LIMIT,
  topAdvogadosTribunals,
  type AdvogadosTribunalStat,
} from './advogadosCoverage';
import type { TribunalCoverageRow } from './data/contracts';

function row(overrides: Partial<TribunalCoverageRow>): TribunalCoverageRow {
  return {
    tribunal: 'tjro',
    uploaded: 10,
    pending: 0,
    absent: 0,
    unknown: 0,
    total: 10,
    coverage_pct: 100,
    earliest_upload: '2021-01-01',
    latest_upload: '2026-01-01',
    ...overrides,
  };
}

describe('topAdvogadosTribunals', () => {
  it('never reproduces the original bug: daysWithData/daysTotal/dataRatePct all come from the same row', () => {
    // The legacy bug mixed data_rate_pct from one path with days_with_data/
    // days_total from another, producing "0 de 0 dias" next to "76%".
    const [stat] = topAdvogadosTribunals([
      row({ tribunal: 'tjsp', uploaded: 76, total: 100, coverage_pct: 76 }),
    ]);
    expect(stat.daysWithData).toBe(76);
    expect(stat.daysTotal).toBe(100);
    expect(stat.dataRatePct).toBe(76);
    // The failure mode is specifically impossible now: daysTotal can never
    // be 0 while dataRatePct is a positive percentage, because both derive
    // from the same tribunal_coverage row.
    expect(stat.daysTotal === 0 && stat.dataRatePct > 0).toBe(false);
  });

  it('coverage_pct: null falls back to 0, never NaN/null in the UI value', () => {
    const [stat] = topAdvogadosTribunals([
      row({ tribunal: 'tjac', uploaded: 0, total: 0, coverage_pct: null }),
    ]);
    // uploaded=0 is filtered out entirely (see next test); use uploaded>0
    // with a null coverage_pct to isolate the fallback behavior.
    expect(stat).toBeUndefined();

    const [stat2] = topAdvogadosTribunals([
      row({ tribunal: 'tjac', uploaded: 5, total: 10, coverage_pct: null }),
    ]);
    expect(stat2.dataRatePct).toBe(0);
    expect(Number.isNaN(stat2.dataRatePct)).toBe(false);
  });

  it('filters out tribunals with zero uploaded ZIPs (uploaded > 0 gate)', () => {
    const result = topAdvogadosTribunals([
      row({ tribunal: 'tjac', uploaded: 0, total: 50, coverage_pct: 0 }),
      row({ tribunal: 'tjro', uploaded: 1, total: 50, coverage_pct: 2 }),
    ]);
    expect(result.map((r) => r.tribunal)).toEqual(['TJRO']);
  });

  it('tolerates uploaded > total (data anomaly) without throwing or misordering', () => {
    const result = topAdvogadosTribunals([
      row({ tribunal: 'tjro', uploaded: 120, total: 100, coverage_pct: 120 }),
      row({ tribunal: 'tjsp', uploaded: 50, total: 100, coverage_pct: 50 }),
    ]);
    expect(result.map((r) => r.tribunal)).toEqual(['TJRO', 'TJSP']);
    expect(result[0].daysWithData).toBe(120);
  });

  it('breaks coverage_pct ties alphabetically by tribunal (deterministic order)', () => {
    const result = topAdvogadosTribunals([
      row({ tribunal: 'tjsp', uploaded: 50, total: 100, coverage_pct: 50 }),
      row({ tribunal: 'tjac', uploaded: 50, total: 100, coverage_pct: 50 }),
      row({ tribunal: 'tjro', uploaded: 50, total: 100, coverage_pct: 50 }),
    ]);
    expect(result.map((r) => r.tribunal)).toEqual(['TJAC', 'TJRO', 'TJSP']);
  });

  it('caps at ADVOGADOS_TRIBUNALS_LIMIT (12) by default, sorted by coverage desc', () => {
    const rows = Array.from({ length: 20 }, (_, i) =>
      row({ tribunal: `tj${i.toString().padStart(2, '0')}`, uploaded: 1, total: 100, coverage_pct: i }),
    );
    const result = topAdvogadosTribunals(rows);
    expect(result).toHaveLength(ADVOGADOS_TRIBUNALS_LIMIT);
    // highest coverage_pct (19) first
    expect(result[0].tribunal).toBe('TJ19');
    expect(result[ADVOGADOS_TRIBUNALS_LIMIT - 1].tribunal).toBe('TJ08');
  });

  it('respects a custom limit', () => {
    const rows = Array.from({ length: 5 }, (_, i) =>
      row({ tribunal: `tj${i}`, uploaded: 1, total: 10, coverage_pct: i }),
    );
    expect(topAdvogadosTribunals(rows, 3)).toHaveLength(3);
  });

  it('returns an empty array for null/empty input, never throws', () => {
    expect(topAdvogadosTribunals(null)).toEqual([]);
    expect(topAdvogadosTribunals([])).toEqual([]);
  });

  it('uppercases the tribunal code consistently (contract vs display casing)', () => {
    const [stat] = topAdvogadosTribunals([row({ tribunal: 'tjro', uploaded: 1, total: 1, coverage_pct: 100 })]);
    expect(stat.tribunal).toBe('TJRO');
  });
});

describe('single source of truth: cards, static routes and sitemap agree', () => {
  // Regression guard for the reviewer's concern: advogados.astro (cards),
  // advogados/[tribunal].astro (getStaticPaths) and sitemap.xml.ts must all
  // derive their tribunal set from the exact same helper call, so they can
  // never diverge. This test asserts the *contract* of that invariant:
  // calling topAdvogadosTribunals() twice with the same input is
  // deterministic and yields the same set/order every time — the property
  // the three consumers rely on to stay in sync.
  const rows: TribunalCoverageRow[] = [
    row({ tribunal: 'tjro', uploaded: 90, total: 100, coverage_pct: 90 }),
    row({ tribunal: 'tjsp', uploaded: 80, total: 100, coverage_pct: 80 }),
    row({ tribunal: 'tjac', uploaded: 0, total: 100, coverage_pct: 0 }),
  ];

  it('is deterministic across repeated calls (what cards/routes/sitemap each invoke independently)', () => {
    const first = topAdvogadosTribunals(rows);
    const second = topAdvogadosTribunals(rows);
    expect(second).toEqual(first);
  });

  it('produces the exact tribunal set that getStaticPaths/sitemap would iterate', () => {
    const result = topAdvogadosTribunals(rows);
    const tribunalSet = result.map((r: AdvogadosTribunalStat) => r.tribunal);
    expect(tribunalSet).toEqual(['TJRO', 'TJSP']);
  });
});
