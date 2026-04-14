/**
 * Typed loaders for query results generated from web/src/queries/*.qmd
 *
 * Each .qmd declares an `output: /data/xxx.json` in its frontmatter.
 * This file provides typed loaders matching those contracts.
 */

export interface TribunalCoverage {
  tribunal: string;
  uploaded: number;
  pending: number;
  absent: number;
  unknown: number;
  total: number;
  coverage_pct: number;
  earliest_upload: string | null;
  latest_upload: string | null;
}

export interface Totals {
  total: number;
  uploaded: number;
  pending: number;
  absent: number;
  unknown: number;
  coverage_pct: number;
  tribunals_total: number;
  tribunals_with_data: number;
}

export interface DailyUpload {
  date: string;
  count: number;
}

export interface StatsCoverage {
  avg_coverage: number;
  best_count: number;
  best_day: string;
  worst_count: number;
  worst_day: string;
}

export interface CourtReliabilityRow {
  court: string;
  collected: number;
  absent: number;
  total: number;
  rate: number;
}

export interface WeeklyPatternRow {
  day_idx: number;
  name: string;
  avg: number;
  days_count: number;
}

const IA_BASE = 'https://archive.org/download/causaganha-dashboard';

async function fetchJson<T>(path: string): Promise<T> {
  // Try local (built) first, fall back to IA for dev/preview
  const res = await fetch(path);
  if (res.ok) return res.json() as Promise<T>;
  throw new Error(`Failed to fetch ${path}: ${res.status}`);
}

export const loadTribunalCoverage = (): Promise<TribunalCoverage[]> =>
  fetchJson<TribunalCoverage[]>('/data/tribunal_coverage.json');

export const loadTotals = (): Promise<Totals> =>
  fetchJson<Totals>('/data/totals.json');

export const loadDailyUploads = (): Promise<DailyUpload[]> =>
  fetchJson<DailyUpload[]>('/data/daily_uploads.json');

export const loadStatsCoverage = (): Promise<StatsCoverage> =>
  fetchJson<StatsCoverage>('/data/stats_coverage.json');

export const loadCourtReliability = (): Promise<CourtReliabilityRow[]> =>
  fetchJson<CourtReliabilityRow[]>('/data/court_reliability.json');

export const loadWeeklyPattern = (): Promise<WeeklyPatternRow[]> =>
  fetchJson<WeeklyPatternRow[]>('/data/weekly_pattern.json');

export { IA_BASE };
