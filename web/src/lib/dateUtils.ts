/**
 * Shared date formatting utilities.
 */

/** Format a Date as an ISO date string (YYYY-MM-DD). */
export function toDateString(date: Date): string {
  return date.toISOString().split('T')[0];
}

/** Get today's date as an ISO date string. */
export function todayString(): string {
  return toDateString(new Date());
}

/** Check whether a year is a leap year. */
export function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

const MS_PER_DAY = 1000 * 60 * 60 * 24;

/** Whole days between two ISO date strings (b - a); negative if b precedes a. */
export function daysBetweenIso(aIso: string, bIso: string): number {
  const a = new Date(aIso + 'T00:00:00Z');
  const b = new Date(bIso + 'T00:00:00Z');
  return Math.floor((b.getTime() - a.getTime()) / MS_PER_DAY);
}

/** Business days (Mon-Fri) per calendar week -- the achievable ceiling for any "per week" rate derived from business-day counts, since manifest.py never records weekends. */
export const BUSINESS_DAYS_PER_WEEK = 5;

/** Whether an ISO date string falls on Mon-Fri, matching manifest.py's `weekday() < 5` build rule. */
export function isBusinessDayIso(iso: string): boolean {
  const day = new Date(iso + 'T00:00:00Z').getUTCDay();
  return day !== 0 && day !== 6;
}

/** Count of business days (Mon-Fri) in the inclusive range [aIso, bIso]. */
export function businessDaysBetweenIso(aIso: string, bIso: string): number {
  let count = 0;
  const cur = new Date(aIso + 'T00:00:00Z');
  const end = new Date(bIso + 'T00:00:00Z');
  while (cur <= end) {
    const day = cur.getUTCDay();
    if (day !== 0 && day !== 6) count++;
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  return count;
}

/** Latest (lexicographically max) ISO date string across one or more arrays, or null if all empty. */
export function latestIsoDate(...dateArrays: string[][]): string | null {
  let latest: string | null = null;
  for (const dates of dateArrays) {
    for (const d of dates) {
      if (!latest || d > latest) latest = d;
    }
  }
  return latest;
}
