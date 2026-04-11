/**
 * Shared color/status mapping utilities for coverage visualization.
 */

export interface CoverageColorPair {
  text: string;
  bg: string;
}

/** Get text + background color classes based on a coverage percentage (0-100). */
export function getCoverageColor(pct: number): CoverageColorPair {
  if (pct >= 90) return { text: 'cg-text-success', bg: 'cg-bg-success' };
  if (pct >= 50) return { text: 'cg-text-warning', bg: 'cg-bg-warning' };
  if (pct > 0) return { text: 'cg-text-danger', bg: 'cg-bg-danger' };
  return { text: 'cg-text-muted', bg: 'cg-bg-muted' };
}

/** Get a single color class string based on a coverage percentage (for heatmap tables). */
export function getCoverageColorClass(pct: number): string {
  if (pct >= 80) return 'cg-text-success cg-bg-success';
  if (pct >= 50) return 'cg-text-warning cg-bg-warning';
  return 'cg-text-danger cg-bg-danger';
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
