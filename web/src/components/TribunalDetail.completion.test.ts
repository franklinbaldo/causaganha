import { cleanup, screen } from '@testing-library/svelte/pure';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TribunalDetailRaw from './TribunalDetail.svelte';
import { render } from './__steps__/shared';

const TribunalDetail = TribunalDetailRaw as unknown as Parameters<typeof render>[0];

function businessDaysBetween(startIso: string, endIso: string): string[] {
  const days: string[] = [];
  const cur = new Date(startIso + 'T00:00:00Z');
  const end = new Date(endIso + 'T00:00:00Z');
  while (cur <= end) {
    const day = cur.getUTCDay();
    if (day !== 0 && day !== 6) days.push(cur.toISOString().split('T')[0]);
    cur.setUTCDate(cur.getUTCDate() + 1);
  }
  return days;
}

// SyncManifest.build() (src/djen_backup/manifest.py) only ever creates
// (tribunal, date) rows for weekdays, so a tribunal collected on every
// business day since its start is genuinely 100% complete -- it should
// show "Concluído" with no false "Destaque de anomalia" card, not be stuck
// around 71% forever because the page's own day-counting includes weekends
// that could never have data.
describe('TribunalDetail — completion for a fully-collected tribunal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-01-16T12:00:00Z')); // Friday
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('reports 100% completion and no anomaly card when every business day was uploaded', () => {
    const start = '2026-01-01';
    const end = '2026-01-16';
    const uploaded = businessDaysBetween(start, end);

    render(TribunalDetail, {
      tribunalCode: 'tjro',
      initialUploadedDates: uploaded,
      initialAbsentDates: [],
      initialStartDate: start,
    });

    expect(screen.getAllByText('Concluído').length).toBeGreaterThan(0);
    expect(screen.getByText('100%')).toBeTruthy();
    expect(screen.queryByText('Destaque de anomalia')).toBeNull();
  });
});
