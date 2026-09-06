import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  partitionByTribunal,
  tribunalCalendarPartitionPath,
  loadTribunalCalendarPartition,
} from './tribunalCalendarPartition';
import type { TribunalCalendarRow } from './tribunalCoverageDrilldown';

const ROWS: TribunalCalendarRow[] = [
  { tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' },
  { tribunal: 'TJRO', date: '2026-01-02', status: 'absent' },
  { tribunal: 'TJSP', date: '2026-06-01', status: 'absent' },
];

describe('partitionByTribunal', () => {
  it('groups rows by tribunal, preserving row shape and order', () => {
    const partitions = partitionByTribunal(ROWS);
    expect(partitions.get('TJRO')).toEqual([
      { tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' },
      { tribunal: 'TJRO', date: '2026-01-02', status: 'absent' },
    ]);
    expect(partitions.get('TJSP')).toEqual([{ tribunal: 'TJSP', date: '2026-06-01', status: 'absent' }]);
  });

  it('never puts one tribunal in another tribunal bucket', () => {
    const partitions = partitionByTribunal(ROWS);
    expect(partitions.get('TJRO')?.every(r => r.tribunal === 'TJRO')).toBe(true);
    expect(partitions.size).toBe(2);
  });

  it('returns an empty map for an empty input', () => {
    expect(partitionByTribunal([]).size).toBe(0);
  });
});

describe('tribunalCalendarPartitionPath', () => {
  it('builds a lowercase, per-tribunal relative path distinct from the global contract file', () => {
    expect(tribunalCalendarPartitionPath('TJRO')).toBe('data/tribunal_calendar_by_tribunal/tjro.json');
    expect(tribunalCalendarPartitionPath('TJRO')).not.toBe('data/tribunal_calendar.json');
  });
});

describe('loadTribunalCalendarPartition', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches only the requested tribunal partition, resolved against publicBase', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' }]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const rows = await loadTribunalCalendarPartition('TJRO', '/causaganha/');

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/causaganha/data/tribunal_calendar_by_tribunal/tjro.json');
    expect(rows).toEqual([{ tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' }]);
  });

  it('returns null (never throws) on a non-OK HTTP response', async () => {
    global.fetch = vi.fn().mockResolvedValue(new Response('not found', { status: 404 })) as unknown as typeof fetch;
    const rows = await loadTribunalCalendarPartition('TJSP', '/');
    expect(rows).toBeNull();
  });

  it('returns null (never throws) on a network failure', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as unknown as typeof fetch;
    const rows = await loadTribunalCalendarPartition('TJSP', '/');
    expect(rows).toBeNull();
  });

  it('returns null on a payload that fails schema validation (e.g. wrong tribunal shape)', async () => {
    global.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ tribunal: 'TJSP' }]), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    ) as unknown as typeof fetch;
    const rows = await loadTribunalCalendarPartition('TJSP', '/');
    expect(rows).toBeNull();
  });
});
