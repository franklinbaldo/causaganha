/**
 * Zod schemas for the .qmd query contracts in web/src/queries/.
 *
 * One schema per contract, with the shape derived from the SQL SELECT list of
 * the corresponding .qmd file (rendered to JSON by scripts/render_queries.py).
 * Schemas are deliberately tolerant on nullability: any column that the SQL
 * can produce as NULL (aggregates over empty sets, FILTERed MIN/MAX, LEFT
 * JOIN-ish unions, CASE without ELSE) is `.nullable()`. Tighten only with
 * observed production data.
 *
 * Contract frontmatter `format:` decides array vs object:
 *   format: array  → z.array(rowSchema)
 *   format: object → single-row object schema
 */
import { z } from 'zod';

// DuckDB dates/timestamps are serialized via .isoformat() by render_queries.py.
const isoDate = z.string();

/** consolidation_status.qmd — format: object */
export const consolidationStatusSchema = z.object({
  total_dates_with_uploads: z.number(),
  dates_fully_uploaded: z.number(),
  dates_partially_uploaded: z.number(),
  earliest_date: isoDate.nullable(),
  latest_date: isoDate.nullable(),
});
export type ConsolidationStatus = z.infer<typeof consolidationStatusSchema>;

/** court_reliability.qmd — format: array */
export const courtReliabilityRowSchema = z.object({
  court: z.string(),
  collected: z.number(),
  absent: z.number(),
  total: z.number(),
  rate: z.number(),
});
export const courtReliabilitySchema = z.array(courtReliabilityRowSchema);
export type CourtReliabilityRow = z.infer<typeof courtReliabilityRowSchema>;

/** daily_uploads.qmd — format: array */
export const dailyUploadRowSchema = z.object({
  date: isoDate,
  count: z.number(),
});
export const dailyUploadsSchema = z.array(dailyUploadRowSchema);
export type DailyUploadRow = z.infer<typeof dailyUploadRowSchema>;

/** datajud_classes.qmd — format: array */
export const datajudClasseRowSchema = z.object({
  classe_nome: z.string(),
  total: z.number(),
});
export const datajudClassesSchema = z.array(datajudClasseRowSchema);
export type DatajudClasseRow = z.infer<typeof datajudClasseRowSchema>;

/** datajud_totals.qmd — format: object (aggregates over empty set → NULL max) */
export const datajudTotalsSchema = z.object({
  total_processos: z.number(),
  total_registros: z.number(),
  total_tribunais: z.number(),
  ultima_atualizacao: isoDate.nullable(),
});
export type DatajudTotals = z.infer<typeof datajudTotalsSchema>;

/** juris_classes.qmd — format: array */
export const jurisClasseRowSchema = z.object({
  classe_judicial: z.string().nullable(),
  total: z.number(),
});
export const jurisClassesSchema = z.array(jurisClasseRowSchema);
export type JurisClasseRow = z.infer<typeof jurisClasseRowSchema>;

/** juris_orgaos.qmd — format: array */
export const jurisOrgaoRowSchema = z.object({
  orgao: z.string().nullable(),
  total: z.number(),
});
export const jurisOrgaosSchema = z.array(jurisOrgaoRowSchema);
export type JurisOrgaoRow = z.infer<typeof jurisOrgaoRowSchema>;

/** juris_totals.qmd — format: object */
export const jurisTotalsSchema = z.object({
  total_documentos: z.number(),
  total_tipos: z.number(),
  total_orgaos: z.number(),
  data_mais_recente: isoDate.nullable(),
});
export type JurisTotals = z.infer<typeof jurisTotalsSchema>;

/** lawyer_leaderboard.qmd — format: array */
export const lawyerLeaderboardRowSchema = z.object({
  lawyer_name: z.string(),
  oab_number: z.union([z.string(), z.number()]).nullable(),
  oab_state: z.string().nullable(),
  rating: z.number(),
  mu: z.number(),
  sigma: z.number(),
  total_cases: z.number(),
  wins: z.number(),
  losses: z.number(),
  win_rate: z.number(),
});
export const lawyerLeaderboardSchema = z.array(lawyerLeaderboardRowSchema);
export type LawyerLeaderboardRow = z.infer<typeof lawyerLeaderboardRowSchema>;

/** processos_multi_fonte.qmd — format: array */
export const processoMultiFonteRowSchema = z.object({
  nr_processo: z.string(),
  nr_processo_mascara: z.string().nullable(),
  n_fontes: z.number(),
  // DuckDB LIST serializes as JSON array; keep a string fallback for older renders.
  fontes: z.union([z.array(z.string()), z.string()]),
  djen_n_publicacoes: z.number().nullable(),
  djen_primeira_pub: isoDate.nullable(),
  djen_ultima_pub: isoDate.nullable(),
  juris_n_documentos: z.number().nullable(),
  juris_classe: z.string().nullable(),
  juris_orgao: z.string().nullable(),
  juris_relator: z.string().nullable(),
  juris_data_julgamento: isoDate.nullable(),
  juris_url: z.string().nullable(),
  stj_tema: z.string().nullable(),
  stj_classe: z.string().nullable(),
  stj_relator: z.string().nullable(),
  stj_data_decisao: isoDate.nullable(),
  tem_datajud: z.boolean(),
  classe_oficial: z.string().nullable(),
});
export const processosMultiFonteSchema = z.array(processoMultiFonteRowSchema);
export type ProcessoMultiFonteRow = z.infer<typeof processoMultiFonteRowSchema>;

/**
 * site_status.qmd — format: object.
 *
 * Canonical global metrics + per-source sync health. `sources` is keyed by
 * data source; only `djen` exists today (the sync-manifest is the sole
 * canonical manifest) — new sources are added as new keys without breaking
 * consumers.
 *
 * The JSON carries raw timestamps (last_attempt_at / last_success_at);
 * freshness ('atualizado' | 'atrasado' | 'desconhecido') is DERIVED at build
 * time in siteStatus.ts from last_success_at — never trusted from the
 * artifact, so a bot stuck on 403s (fresh attempts, stale successes) cannot
 * keep the dashboard green.
 */
const isoDateTime = z.iso.datetime({ offset: true });

export const siteStatusSourceSchema = z.object({
  /** Pares (tribunal × dia) com ZIP confirmado no Internet Archive. */
  zips_archived: z.number(),
  /** Total de pares (tribunal × dia) rastreados no manifesto. */
  pairs_total: z.number(),
  tribunals_with_data: z.number(),
  tribunals_total: z.number(),
  coverage_pct: z.number().nullable(),
  /** Primeira data rastreada no manifesto (uploaded ou não). */
  earliest_tracked_date: isoDate.nullable(),
  earliest_upload_date: isoDate.nullable(),
  latest_upload_date: isoDate.nullable(),
  /** Pares onde o DJEN confirmou não haver publicação (404/400/"Sem comunicações"). */
  absent_confirmed: z.number(),
  /** Pares com caderno confirmado no DJEN (200 + URL) mas sem ZIP no IA. */
  pending_real: z.number(),
  /**
   * Idade (horas) do par pending_real mais antigo; null quando pending_real é
   * zero. Opcional (não apenas nullable): um artefato/fixture publicado
   * antes deste campo existir não deve falhar o parse — ver
   * docs/SERVICE_OBJECTIVES.md.
   */
  pending_real_max_age_hours: z.number().nullable().optional(),
  /** Pares cuja última resposta foi inconclusiva (403/5xx/timeout/network). */
  errors_transient: z.number(),
  /** Pares nunca verificados (sem resposta DJEN nem upload). */
  never_checked: z.number(),
  /** max(updated_at) do manifesto — qualquer tentativa, inclusive falhas. */
  last_attempt_at: isoDateTime.nullable(),
  /** max(updated_at) restrito a tentativas conclusivas (ver site_status.qmd). */
  last_success_at: isoDateTime.nullable(),
});
export type SiteStatusSource = z.infer<typeof siteStatusSourceSchema>;

export const siteStatusSchema = z.object({
  generated_at: isoDateTime,
  sources: z.object({
    djen: siteStatusSourceSchema,
  }),
});
export type SiteStatus = z.infer<typeof siteStatusSchema>;

/** stats_coverage.qmd — format: object (aggregates over empty window → NULLs) */
export const statsCoverageSchema = z.object({
  avg_coverage: z.number().nullable(),
  best_count: z.number().nullable(),
  best_day: isoDate.nullable(),
  worst_count: z.number().nullable(),
  worst_day: isoDate.nullable(),
});
export type StatsCoverage = z.infer<typeof statsCoverageSchema>;

/** stj_relatores.qmd — format: array */
export const stjRelatorRowSchema = z.object({
  ministroRelator: z.string().nullable(),
  total: z.number(),
});
export const stjRelatoresSchema = z.array(stjRelatorRowSchema);
export type StjRelatorRow = z.infer<typeof stjRelatorRowSchema>;

/** stj_temas.qmd — format: array */
export const stjTemaRowSchema = z.object({
  tema: z.string().nullable(),
  total: z.number(),
});
export const stjTemasSchema = z.array(stjTemaRowSchema);
export type StjTemaRow = z.infer<typeof stjTemaRowSchema>;

/** stj_totals.qmd — format: object */
export const stjTotalsSchema = z.object({
  total: z.number(),
  total_temas: z.number(),
  ultima_decisao: isoDate.nullable(),
});
export type StjTotals = z.infer<typeof stjTotalsSchema>;

/** totals.qmd — format: object */
export const totalsSchema = z.object({
  total: z.number(),
  uploaded: z.number(),
  pending: z.number(),
  absent: z.number(),
  unknown: z.number(),
  coverage_pct: z.number().nullable(),
  tribunals_total: z.number(),
  tribunals_with_data: z.number(),
});
export type Totals = z.infer<typeof totalsSchema>;

/** tribunal_calendar.qmd — format: array */
export const tribunalCalendarRowSchema = z.object({
  tribunal: z.string(),
  date: isoDate,
  status: z.enum(['uploaded', 'absent']),
});
export const tribunalCalendarSchema = z.array(tribunalCalendarRowSchema);
export type TribunalCalendarRow = z.infer<typeof tribunalCalendarRowSchema>;

/** tribunal_coverage.qmd — format: array */
export const tribunalCoverageRowSchema = z.object({
  tribunal: z.string(),
  uploaded: z.number(),
  pending: z.number(),
  absent: z.number(),
  unknown: z.number(),
  total: z.number(),
  coverage_pct: z.number().nullable(),
  earliest_upload: isoDate.nullable(),
  latest_upload: isoDate.nullable(),
});
export const tribunalCoverageSchema = z.array(tribunalCoverageRowSchema);
export type TribunalCoverageRow = z.infer<typeof tribunalCoverageRowSchema>;

/** weekly_pattern.qmd — format: array (DOW ∈ 0..6, AVG over non-empty group) */
export const weeklyPatternRowSchema = z.object({
  day_idx: z.number(),
  name: z.string(),
  avg: z.number(),
  days_count: z.number(),
});
export const weeklyPatternSchema = z.array(weeklyPatternRowSchema);
export type WeeklyPatternRow = z.infer<typeof weeklyPatternRowSchema>;

/**
 * Registry: contract name → { output file (relative to public/), schema }.
 * Names mirror the .qmd basenames in web/src/queries/.
 */
export const contracts = {
  consolidation_status: { output: 'data/consolidation_status.json', schema: consolidationStatusSchema },
  court_reliability: { output: 'data/court_reliability.json', schema: courtReliabilitySchema },
  daily_uploads: { output: 'data/daily_uploads.json', schema: dailyUploadsSchema },
  datajud_classes: { output: 'data/datajud_classes.json', schema: datajudClassesSchema },
  datajud_totals: { output: 'data/datajud_totals.json', schema: datajudTotalsSchema },
  juris_classes: { output: 'data/juris_classes.json', schema: jurisClassesSchema },
  juris_orgaos: { output: 'data/juris_orgaos.json', schema: jurisOrgaosSchema },
  juris_totals: { output: 'data/juris_totals.json', schema: jurisTotalsSchema },
  lawyer_leaderboard: { output: 'data/lawyer_leaderboard.json', schema: lawyerLeaderboardSchema },
  processos_multi_fonte: { output: 'data/processos_multi_fonte.json', schema: processosMultiFonteSchema },
  site_status: { output: 'data/site-status.json', schema: siteStatusSchema },
  stats_coverage: { output: 'data/stats_coverage.json', schema: statsCoverageSchema },
  stj_relatores: { output: 'data/stj_relatores.json', schema: stjRelatoresSchema },
  stj_temas: { output: 'data/stj_temas.json', schema: stjTemasSchema },
  stj_totals: { output: 'data/stj_totals.json', schema: stjTotalsSchema },
  totals: { output: 'data/totals.json', schema: totalsSchema },
  tribunal_calendar: { output: 'data/tribunal_calendar.json', schema: tribunalCalendarSchema },
  tribunal_coverage: { output: 'data/tribunal_coverage.json', schema: tribunalCoverageSchema },
  weekly_pattern: { output: 'data/weekly_pattern.json', schema: weeklyPatternSchema },
} as const satisfies Record<string, { output: string; schema: z.ZodType }>;

export type ContractName = keyof typeof contracts;
export type ContractData<K extends ContractName> = z.infer<(typeof contracts)[K]['schema']>;
