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
