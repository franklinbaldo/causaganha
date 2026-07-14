import fs from 'node:fs';
import path from 'node:path';

/**
 * Minimal structural types for the JSON artifacts under `public/`. These
 * files are produced by the Python pipeline and the shapes are loose by
 * necessity (new fields land all the time), so each type documents only the
 * subset the Astro pages actively read from.
 */
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
