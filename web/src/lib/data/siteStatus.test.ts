import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  loadSiteStatus,
  evaluateSourceFreshness,
  freshnessDisplayLabel,
  formatUtcDateTime,
  utcDateTimeAttr,
  parseTimestamp,
  pctOfTotal,
  STALE_BUILD_LIMIT_MS,
  MAX_FUTURE_SKEW_MS,
  FRESHNESS_THRESHOLD_MS,
} from './siteStatus';

/** Relógio fixo para todos os testes — nenhum helper usa Date.now() interno. */
const NOW = Date.parse('2026-07-12T12:00:00Z');

const HOUR = 60 * 60 * 1000;

function iso(msEpoch: number): string {
  return new Date(msEpoch).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

/** JSON válido do contrato site_status; overrides mesclados em sources.djen. */
function validStatus(djenOverrides: Record<string, unknown> = {}) {
  return {
    generated_at: iso(NOW - HOUR),
    sources: {
      djen: {
        zips_archived: 43_634,
        pairs_total: 163_464,
        tribunals_with_data: 63,
        tribunals_total: 66,
        coverage_pct: 26.7,
        earliest_tracked_date: '2025-01-01',
        earliest_upload_date: '2025-01-02',
        latest_upload_date: '2026-07-10',
        absent_confirmed: 119_830,
        pending_real: 0,
        pending_real_max_age_hours: null,
        errors_transient: 0,
        never_checked: 0,
        last_attempt_at: iso(NOW - 2 * HOUR),
        last_success_at: iso(NOW - 2 * HOUR),
        ...djenOverrides,
      },
    },
  };
}

describe('loadSiteStatus', () => {
  let publicDir: string;

  beforeEach(() => {
    publicDir = mkdtempSync(join(tmpdir(), 'cg-site-status-'));
    mkdirSync(join(publicDir, 'data'), { recursive: true });
  });

  afterEach(() => {
    rmSync(publicDir, { recursive: true, force: true });
  });

  function write(content: string): void {
    writeFileSync(join(publicDir, 'data', 'site-status.json'), content);
  }

  it('throws when the file is missing (mandatory contract, no EmptyState)', async () => {
    await expect(loadSiteStatus(publicDir, NOW)).rejects.toThrow(/ausente/);
  });

  it('throws on invalid JSON', async () => {
    write('{not json');
    await expect(loadSiteStatus(publicDir, NOW)).rejects.toThrow(/site_status/);
  });

  it('throws when generated_at is not an ISO datetime (Zod rejects)', async () => {
    write(JSON.stringify({ ...validStatus(), generated_at: 'ontem' }));
    await expect(loadSiteStatus(publicDir, NOW)).rejects.toThrow(/site_status/);
  });

  it('throws when the artifact is older than 7 days', async () => {
    write(
      JSON.stringify({
        ...validStatus(),
        generated_at: iso(NOW - STALE_BUILD_LIMIT_MS - HOUR),
      }),
    );
    await expect(loadSiteStatus(publicDir, NOW)).rejects.toThrow(/obsoleto/);
  });

  it('throws when generated_at is in the future beyond the 5 min skew', async () => {
    write(
      JSON.stringify({
        ...validStatus(),
        generated_at: iso(NOW + MAX_FUTURE_SKEW_MS + 60_000),
      }),
    );
    await expect(loadSiteStatus(publicDir, NOW)).rejects.toThrow(/futuro/);
  });

  it('accepts generated_at slightly in the future (within clock skew)', async () => {
    write(
      JSON.stringify({
        ...validStatus(),
        generated_at: iso(NOW + MAX_FUTURE_SKEW_MS - 60_000),
      }),
    );
    await expect(loadSiteStatus(publicDir, NOW)).resolves.toBeTruthy();
  });

  it('throws when last_success_at is not a valid ISO datetime', async () => {
    write(JSON.stringify(validStatus({ last_success_at: 'Invalid Date' })));
    await expect(loadSiteStatus(publicDir, NOW)).rejects.toThrow(/site_status/);
  });

  it('accepts tribunals_total = 0 (CI stub) — guarding is the page math job', async () => {
    write(
      JSON.stringify(
        validStatus({
          tribunals_total: 0,
          tribunals_with_data: 0,
          zips_archived: 0,
          pairs_total: 0,
          coverage_pct: null,
          absent_confirmed: 0,
          last_attempt_at: null,
          last_success_at: null,
        }),
      ),
    );
    const status = await loadSiteStatus(publicDir, NOW);
    expect(status.sources.djen.tribunals_total).toBe(0);
  });
});

describe('evaluateSourceFreshness', () => {
  it('recent success → atualizado', () => {
    const sf = evaluateSourceFreshness(
      { last_attempt_at: iso(NOW - HOUR), last_success_at: iso(NOW - 2 * HOUR) },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atualizado', failingRecently: false });
  });

  it('success in the future beyond clock skew → never atualizado', () => {
    const sf = evaluateSourceFreshness(
      {
        last_attempt_at: iso(NOW - FRESHNESS_THRESHOLD_MS - 24 * HOUR),
        last_success_at: iso(NOW + MAX_FUTURE_SKEW_MS + 60_000),
      },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atrasado', failingRecently: false });
  });

  it('success slightly in the future (within clock skew) → atualizado', () => {
    const sf = evaluateSourceFreshness(
      {
        last_attempt_at: iso(NOW - HOUR),
        last_success_at: iso(NOW + MAX_FUTURE_SKEW_MS - 60_000),
      },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atualizado', failingRecently: false });
  });

  it('attempt in the future beyond clock skew does not count as recent activity', () => {
    const sf = evaluateSourceFreshness(
      {
        last_attempt_at: iso(NOW + MAX_FUTURE_SKEW_MS + 60_000),
        last_success_at: iso(NOW - FRESHNESS_THRESHOLD_MS - 24 * HOUR),
      },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atrasado', failingRecently: false });
  });

  it('recent attempt + old success → atrasado with failingRecently (continuous failure is visible)', () => {
    const sf = evaluateSourceFreshness(
      {
        last_attempt_at: iso(NOW - HOUR),
        last_success_at: iso(NOW - FRESHNESS_THRESHOLD_MS - 24 * HOUR),
      },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atrasado', failingRecently: true });
  });

  it('old attempt + old success → atrasado without recent activity', () => {
    const old = iso(NOW - FRESHNESS_THRESHOLD_MS - 24 * HOUR);
    const sf = evaluateSourceFreshness(
      { last_attempt_at: old, last_success_at: old },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atrasado', failingRecently: false });
  });

  it('recent attempt but never a success → atrasado + failingRecently, never atualizado', () => {
    const sf = evaluateSourceFreshness(
      { last_attempt_at: iso(NOW - HOUR), last_success_at: null },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'atrasado', failingRecently: true });
  });

  it('no timestamps at all → desconhecido', () => {
    const sf = evaluateSourceFreshness(
      { last_attempt_at: null, last_success_at: null },
      NOW,
    );
    expect(sf).toEqual({ freshness: 'desconhecido', failingRecently: false });
  });

  it('success exactly at the 48h threshold still counts as atualizado', () => {
    const sf = evaluateSourceFreshness(
      {
        last_attempt_at: iso(NOW),
        last_success_at: iso(NOW - FRESHNESS_THRESHOLD_MS),
      },
      NOW,
    );
    expect(sf.freshness).toBe('atualizado');
  });
});

describe('freshnessDisplayLabel', () => {
  it('labels continuous failure explicitly', () => {
    expect(
      freshnessDisplayLabel({ freshness: 'atrasado', failingRecently: true }),
    ).toBe('Atrasado — tentativas recentes falhando');
  });

  it('uses the plain label otherwise', () => {
    expect(
      freshnessDisplayLabel({ freshness: 'atrasado', failingRecently: false }),
    ).toBe('Atrasado');
    expect(
      freshnessDisplayLabel({ freshness: 'atualizado', failingRecently: false }),
    ).toBe('Atualizado');
    expect(
      freshnessDisplayLabel({ freshness: 'desconhecido', failingRecently: false }),
    ).toBe('Desconhecido');
  });
});

describe('timestamp display helpers', () => {
  it('parseTimestamp: null/empty/garbage → null (never NaN)', () => {
    expect(parseTimestamp(null)).toBeNull();
    expect(parseTimestamp(undefined)).toBeNull();
    expect(parseTimestamp('')).toBeNull();
    expect(parseTimestamp('não é data')).toBeNull();
  });

  it('formatUtcDateTime: invalid input → null, so pages render an explicit fallback', () => {
    expect(formatUtcDateTime('Invalid Date')).toBeNull();
    expect(formatUtcDateTime(null)).toBeNull();
  });

  it('utcDateTimeAttr: invalid input → null, so <time> is omitted instead of carrying junk', () => {
    expect(utcDateTimeAttr('Invalid Date')).toBeNull();
    expect(utcDateTimeAttr(null)).toBeNull();
    expect(utcDateTimeAttr(undefined)).toBeNull();
  });

  it('utcDateTimeAttr: emits ISO 8601 UTC for the same instant the human label shows', () => {
    const raw = '2026-07-10T08:30:00Z';
    expect(utcDateTimeAttr(raw)).toBe('2026-07-10T08:30:00.000Z');
    expect(formatUtcDateTime(raw)).toContain('10/07/2026');
  });

  it('utcDateTimeAttr: normalises a non-UTC offset to the same instant', () => {
    expect(utcDateTimeAttr('2026-07-10T05:30:00-03:00')).toBe('2026-07-10T08:30:00.000Z');
  });

  it('formatUtcDateTime: valid ISO renders pt-BR UTC, never "Invalid Date UTC"', () => {
    const label = formatUtcDateTime('2026-07-10T08:30:00Z');
    expect(label).toContain('10/07/2026');
    expect(label).toContain('UTC');
    expect(label).not.toContain('Invalid');
  });
});

describe('pctOfTotal (division-by-zero guard for stats.astro)', () => {
  it('returns 0 when total is 0 (CI stub tribunals_total) — never NaN', () => {
    expect(pctOfTotal(10, 0)).toBe(0);
    expect(Number.isNaN(pctOfTotal(0, 0))).toBe(false);
  });

  it('computes the percentage otherwise', () => {
    expect(pctOfTotal(33, 66)).toBe(50);
  });
});
