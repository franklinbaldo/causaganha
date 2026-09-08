import { describe, expect, it } from 'vitest';
import { businessDaysBetweenIso, isBusinessDayIso } from './dateUtils';

describe('isBusinessDayIso', () => {
  it('treats Monday through Friday as business days', () => {
    expect(isBusinessDayIso('2026-01-12')).toBe(true); // Monday
    expect(isBusinessDayIso('2026-01-13')).toBe(true); // Tuesday
    expect(isBusinessDayIso('2026-01-16')).toBe(true); // Friday
  });

  it('treats Saturday and Sunday as non-business days', () => {
    expect(isBusinessDayIso('2026-01-17')).toBe(false); // Saturday
    expect(isBusinessDayIso('2026-01-18')).toBe(false); // Sunday
  });
});

describe('businessDaysBetweenIso', () => {
  it('counts 5 business days across one full Mon-Sun week', () => {
    // Manifest.build() only ever creates (tribunal, date) rows for weekdays
    // (src/djen_backup/manifest.py: `if current.weekday() < 5`), so any
    // "expected days" denominator derived from a date range must match that
    // weekday-only model, not count every calendar day.
    expect(businessDaysBetweenIso('2026-01-12', '2026-01-18')).toBe(5);
  });

  it('counts a single business day when the range is one weekday', () => {
    expect(businessDaysBetweenIso('2026-01-14', '2026-01-14')).toBe(1);
  });

  it('counts zero business days when the range is entirely a weekend', () => {
    expect(businessDaysBetweenIso('2026-01-17', '2026-01-18')).toBe(0);
  });
});
