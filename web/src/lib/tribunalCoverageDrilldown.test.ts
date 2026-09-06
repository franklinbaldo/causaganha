import { describe, expect, it } from 'vitest';
import {
  buildDailyStates,
  summarizeDailyStates,
  parseDrilldownQuery,
  buildDrilldownQuery,
  type TribunalCalendarRow,
} from './tribunalCoverageDrilldown';

const ROWS: TribunalCalendarRow[] = [
  { tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' },
  { tribunal: 'TJRO', date: '2026-01-02', status: 'uploaded' },
  { tribunal: 'TJRO', date: '2026-01-03', status: 'absent' },
  { tribunal: 'TJRO', date: '2026-01-05', status: 'uploaded' },
  { tribunal: 'TJSP', date: '2026-01-01', status: 'absent' },
];

describe('buildDailyStates', () => {
  it('classifies each day in range as uploaded, absent, or sem_evidencia', () => {
    const states = buildDailyStates(ROWS, 'TJRO', '2026-01-01', '2026-01-05');
    expect(states).toEqual([
      { date: '2026-01-01', status: 'uploaded' },
      { date: '2026-01-02', status: 'uploaded' },
      { date: '2026-01-03', status: 'absent' },
      { date: '2026-01-04', status: 'sem_evidencia' },
      { date: '2026-01-05', status: 'uploaded' },
    ]);
  });

  it('never classifies a day missing from the contract as absent (day 4 above is sem_evidencia, not absent)', () => {
    const states = buildDailyStates(ROWS, 'TJRO', '2026-01-04', '2026-01-04');
    expect(states).toEqual([{ date: '2026-01-04', status: 'sem_evidencia' }]);
  });

  it('filters strictly by tribunal', () => {
    const states = buildDailyStates(ROWS, 'TJSP', '2026-01-01', '2026-01-01');
    expect(states).toEqual([{ date: '2026-01-01', status: 'absent' }]);
  });

  it('returns an empty array when start is after end', () => {
    expect(buildDailyStates(ROWS, 'TJRO', '2026-01-05', '2026-01-01')).toEqual([]);
  });
});

describe('summarizeDailyStates', () => {
  it('counts each status and computes coveragePct over observed days only', () => {
    const states = buildDailyStates(ROWS, 'TJRO', '2026-01-01', '2026-01-05');
    expect(summarizeDailyStates(states)).toEqual({
      uploaded: 3,
      absent: 1,
      semEvidencia: 1,
      totalDays: 5,
      coveragePct: 75,
    });
  });

  it('returns coveragePct null when no day in range is observed, instead of fabricating 0%', () => {
    const states = buildDailyStates([], 'TJRO', '2026-01-01', '2026-01-02');
    expect(summarizeDailyStates(states)).toEqual({
      uploaded: 0,
      absent: 0,
      semEvidencia: 2,
      totalDays: 2,
      coveragePct: null,
    });
  });
});

describe('parity with the tribunal_calendar contract', () => {
  it('sums uploaded/absent over the min-max date span of a tribunal to exactly the contract row counts for that tribunal, with no loss or duplication', () => {
    const tribunal = 'TJRO';
    const rowsForTribunal = ROWS.filter((r) => r.tribunal === tribunal);
    const dates = rowsForTribunal.map((r) => r.date).sort();
    const start = dates[0];
    const end = dates[dates.length - 1];

    const states = buildDailyStates(ROWS, tribunal, start, end);
    const summary = summarizeDailyStates(states);

    const expectedUploaded = rowsForTribunal.filter((r) => r.status === 'uploaded').length;
    const expectedAbsent = rowsForTribunal.filter((r) => r.status === 'absent').length;

    expect(summary.uploaded).toBe(expectedUploaded);
    expect(summary.absent).toBe(expectedAbsent);
  });
});

const KNOWN_TRIBUNALS = ['TJRO', 'TJSP'];
const DEFAULTS = { tribunal: 'TJRO', start: '2024-01-01', end: '2026-01-01' };

describe('parseDrilldownQuery', () => {
  it('reads tribunal/start/end from a valid querystring', () => {
    const params = new URLSearchParams('tribunal=TJSP&start=2025-01-01&end=2025-06-30');
    expect(parseDrilldownQuery(params, KNOWN_TRIBUNALS, DEFAULTS)).toEqual({
      tribunal: 'TJSP',
      start: '2025-01-01',
      end: '2025-06-30',
    });
  });

  it('falls back to defaults for an unknown tribunal', () => {
    const params = new URLSearchParams('tribunal=NAOEXISTE&start=2025-01-01&end=2025-06-30');
    expect(parseDrilldownQuery(params, KNOWN_TRIBUNALS, DEFAULTS)).toEqual({
      tribunal: DEFAULTS.tribunal,
      start: '2025-01-01',
      end: '2025-06-30',
    });
  });

  it('falls back to defaults for malformed dates', () => {
    const params = new URLSearchParams('tribunal=TJSP&start=not-a-date&end=2025-06-30');
    expect(parseDrilldownQuery(params, KNOWN_TRIBUNALS, DEFAULTS)).toEqual({
      tribunal: 'TJSP',
      start: DEFAULTS.start,
      end: '2025-06-30',
    });
  });

  it('falls back to all defaults on empty query', () => {
    expect(parseDrilldownQuery(new URLSearchParams(''), KNOWN_TRIBUNALS, DEFAULTS)).toEqual(DEFAULTS);
  });
});

describe('buildDrilldownQuery', () => {
  it('round-trips through parseDrilldownQuery', () => {
    const state = { tribunal: 'TJSP', start: '2025-01-01', end: '2025-06-30' };
    const params = buildDrilldownQuery(state);
    expect(parseDrilldownQuery(params, KNOWN_TRIBUNALS, DEFAULTS)).toEqual(state);
  });
});
