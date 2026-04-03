/**
 * Shared color/status mapping utilities for coverage visualization.
 */

export interface CoverageColorPair {
  text: string;
  bg: string;
}

/** Get text + background color classes based on a coverage percentage (0-100). */
export function getCoverageColor(pct: number): CoverageColorPair {
  if (pct >= 90) return { text: 'text-green-600 dark:text-green-400', bg: 'bg-green-500' };
  if (pct >= 50) return { text: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-500' };
  if (pct > 0) return { text: 'text-red-600 dark:text-red-400', bg: 'bg-red-500' };
  return { text: 'text-gray-400 dark:text-gray-500', bg: 'bg-gray-300 dark:bg-gray-600' };
}

/** Get a single color class string based on a coverage percentage (for heatmap tables). */
export function getCoverageColorClass(pct: number): string {
  if (pct >= 80) return 'text-success bg-success';
  if (pct >= 50) return 'text-warning bg-warning';
  return 'text-danger bg-danger';
}

/** Cell status types used in heatmap grids. */
export type CellStatus = 'outside' | 'collected' | 'absent' | 'missing';

/** Color classes for heatmap cell statuses. */
export const CELL_STATUS_COLORS: Record<CellStatus, string> = {
  outside: 'bg-gray-50 dark:bg-slate-800 hover:bg-border opacity-30',
  collected: 'bg-success hover:bg-success-hover shadow-[inset_0_0_10px_rgba(255,255,255,0.1)]',
  absent: 'bg-warning hover:bg-warning-hover opacity-80',
  missing: 'bg-danger hover:bg-danger-hover',
};

/** Bar color based on collected count (for velocity timeline). */
export function getBarColor(collected: number): string {
  if (collected === 0) return 'bg-danger';
  if (collected < 4) return 'bg-warning';
  return 'bg-success';
}
