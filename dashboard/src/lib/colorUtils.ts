/**
 * Shared color/status mapping utilities for coverage visualization.
 */

export interface CoverageColorPair {
  text: string;
  bg: string;
}

/** Get text + background color classes based on a coverage percentage (0-100). */
export function getCoverageColor(pct: number): CoverageColorPair {
  if (pct >= 90) return { text: 'has-text-success', bg: 'has-background-success' };
  if (pct >= 50) return { text: 'has-text-warning', bg: 'has-background-warning' };
  if (pct > 0) return { text: 'has-text-danger', bg: 'has-background-danger' };
  return { text: 'has-text-grey', bg: 'has-background-grey-light' };
}

/** Get a single color class string based on a coverage percentage (for heatmap tables). */
export function getCoverageColorClass(pct: number): string {
  if (pct >= 80) return 'has-text-success has-background-success';
  if (pct >= 50) return 'has-text-warning has-background-warning';
  return 'has-text-danger has-background-danger';
}

/** Cell status types used in heatmap grids. */
export type CellStatus = 'outside' | 'collected' | 'absent' | 'missing';

/** Color classes for heatmap cell statuses. */
export const CELL_STATUS_COLORS: Record<CellStatus, string> = {
  outside: 'heatmap-outside',
  collected: 'heatmap-collected',
  absent: 'heatmap-absent',
  missing: 'heatmap-missing',
};

/** Bar color based on collected count (for velocity timeline). */
export function getBarColor(collected: number): string {
  if (collected === 0) return 'bar-danger';
  if (collected < 4) return 'bar-warning';
  return 'bar-success';
}
