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

export interface CacheBackfillFile {
  [key: string]: unknown;
}

export function readJson<T = unknown>(relativePath: string): T | null {
  try {
    const fullPath = path.resolve('./public', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf-8')) as T;
  } catch { return null; }
}
