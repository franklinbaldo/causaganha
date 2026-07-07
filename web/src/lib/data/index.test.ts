import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { loadContractBuildTime } from './index';

describe('loadContractBuildTime', () => {
  let publicDir: string;

  beforeEach(() => {
    publicDir = mkdtempSync(join(tmpdir(), 'cg-data-'));
    mkdirSync(join(publicDir, 'data'), { recursive: true });
  });

  afterEach(() => {
    rmSync(publicDir, { recursive: true, force: true });
  });

  it('returns null when the contract JSON is missing (stub build)', async () => {
    await expect(loadContractBuildTime('totals', publicDir)).resolves.toBeNull();
  });

  it('parses and types valid contract JSON', async () => {
    writeFileSync(
      join(publicDir, 'data', 'totals.json'),
      JSON.stringify({
        total: 157000,
        uploaded: 120000,
        pending: 5000,
        absent: 30000,
        unknown: 2000,
        coverage_pct: 76.4,
        tribunals_total: 96,
        tribunals_with_data: 95,
      }),
    );
    const totals = await loadContractBuildTime('totals', publicDir);
    expect(totals).not.toBeNull();
    expect(totals?.uploaded).toBe(120000);
    expect(totals?.coverage_pct).toBe(76.4);
  });

  it('accepts SQL-nullable fields as null', async () => {
    writeFileSync(
      join(publicDir, 'data', 'stats_coverage.json'),
      JSON.stringify({
        avg_coverage: null,
        best_count: null,
        best_day: null,
        worst_count: null,
        worst_day: null,
      }),
    );
    const coverage = await loadContractBuildTime('stats_coverage', publicDir);
    expect(coverage).toEqual({
      avg_coverage: null,
      best_count: null,
      best_day: null,
      worst_count: null,
      worst_day: null,
    });
  });

  it('throws naming the contract on malformed JSON (fails the build)', async () => {
    writeFileSync(join(publicDir, 'data', 'totals.json'), '{ not json !!!');
    await expect(loadContractBuildTime('totals', publicDir)).rejects.toThrow(
      /Contrato de dados "totals"/,
    );
  });

  it('throws naming the contract on schema violation', async () => {
    writeFileSync(
      join(publicDir, 'data', 'court_reliability.json'),
      JSON.stringify([{ court: 'TJRO', collected: 'many', absent: 0, total: 1, rate: 1 }]),
    );
    await expect(loadContractBuildTime('court_reliability', publicDir)).rejects.toThrow(
      /Contrato de dados "court_reliability"/,
    );
  });

  it('rejects an object payload for an array contract', async () => {
    writeFileSync(join(publicDir, 'data', 'daily_uploads.json'), JSON.stringify({ date: 'x' }));
    await expect(loadContractBuildTime('daily_uploads', publicDir)).rejects.toThrow(
      /Contrato de dados "daily_uploads"/,
    );
  });
});
