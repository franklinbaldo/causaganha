import fs from 'node:fs';
import path from 'node:path';

/**
 * Minimal structural types for the JSON artifacts under `public/`. These
 * files are produced by the Python pipeline and the shapes are loose by
 * necessity (new fields land all the time), so each type documents only the
 * subset the Astro pages actively read from.
 */
export interface IaSnapshotItem {
  tribunal: string;
  year?: number;
  zip_count: number;
  total_size_bytes?: number;
  dates?: string[];
  latest_date: string;
  earliest_date: string;
}

export interface IaSnapshotSummary {
  total_items?: number;
  total_zips?: number;
  total_size_gb?: number;
  tribunals_with_data?: number;
  tribunals_total?: number;
  latest_collection_date?: string;
  total_parquets?: number;
}

export interface IaSnapshot {
  generated_at?: string;
  years?: number[];
  items?: Record<string, IaSnapshotItem>;
  summary?: IaSnapshotSummary;
  by_year?: Record<
    string,
    { zip_count?: number; tribunals_with_data?: number; tribunals_total?: number }
  >;
}

export interface CacheTodayFile {
  pipeline?: {
    backfill_total?: number;
    backfill_done?: number;
  };
  files_today?: number;
  tribunal_status?: Record<
    string,
    { status?: string; last_update?: string | null; doc_count?: number }
  >;
  [key: string]: unknown;
}

/**
 * Per-tribunal coverage entry inside `cache/backfill.json` → `tribunal_stats`.
 * Produced by the Python pipeline; every field is optional by necessity.
 */
export interface BackfillTribunalStat {
  tribunal?: string | null;
  data_rate_pct?: number | null;
  days_with_data?: number | null;
  days_total?: number | null;
}

export interface CacheBackfillFile {
  tribunal_stats?: BackfillTribunalStat[];
  archive_snapshot?: IaSnapshot;
  [key: string]: unknown;
}

/**
 * Widgets rendered on the homepage. Generated once per day by
 * `scripts/generate_homepage_widgets.py` and committed to
 * `web/public/cache/homepage-widgets.json` via CI.
 */
export interface HomepageWidgets {
  schema_version?: number;
  generated_at?: string;
  year?: number;
  activity_summary?: {
    periodo?: string;
    intimacoes?: number;
    oabs_unicas?: number;
    processos?: number;
    tribunais?: number;
  };
  top_tribunais_30d?: Array<{ tribunal: string; comunicacoes: number }>;
  top_advogados_atividade?: Array<{
    oab: string;
    uf: string;
    nome?: string | null;
    comunicacoes: number;
    tribunal_principal?: string | null;
    polos?: { A?: number; P?: number };
  }>;
}

export function readJson<T = unknown>(relativePath: string): T | null {
  try {
    const fullPath = path.resolve('./public', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf-8')) as T;
  } catch { return null; }
}

export function readArchiveSnapshot<T = IaSnapshot>(): T | null {
  const backfill = readJson<{ archive_snapshot?: T }>('cache/backfill.json');
  return backfill?.archive_snapshot ?? null;
}
