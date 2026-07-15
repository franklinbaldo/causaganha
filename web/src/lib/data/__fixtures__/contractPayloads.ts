import type { ContractName } from '../contracts';

export const validContractPayloads = {
  consolidation_status: { total_dates_with_uploads: 1, dates_fully_uploaded: 1, dates_partially_uploaded: 0, earliest_date: '2026-04-01', latest_date: '2026-04-01' },
  court_reliability: [{ court: 'TJSP', collected: 1, absent: 0, total: 1, rate: 1 }],
  daily_uploads: [{ date: '2026-04-01', count: 1 }],
  datajud_classes: [{ classe_nome: 'Procedimento Comum', total: 1 }],
  datajud_totals: { total_processos: 1, total_registros: 1, total_tribunais: 1, ultima_atualizacao: '2026-04-01' },
  juris_classes: [{ classe_judicial: null, total: 1 }],
  juris_orgaos: [{ orgao: null, total: 1 }],
  juris_totals: { total_documentos: 1, total_tipos: 1, total_orgaos: 1, data_mais_recente: '2026-04-01' },
  lawyer_leaderboard: [{ lawyer_name: 'DRA MARIA OLIVEIRA', oab_number: '12345', oab_state: 'SP', rating: 25, mu: 25, sigma: 8.333, total_cases: 1, wins: 1, losses: 0, win_rate: 1 }],
  processos_multi_fonte: [{ nr_processo: '00012345620268260100', nr_processo_mascara: '0001234-56.2026.8.26.0100', n_fontes: 1, fontes: ['djen'], djen_n_publicacoes: 1, djen_primeira_pub: '2026-04-01', djen_ultima_pub: '2026-04-01', juris_n_documentos: null, juris_classe: null, juris_orgao: null, juris_relator: null, juris_data_julgamento: null, juris_url: null, stj_tema: null, stj_classe: null, stj_relator: null, stj_data_decisao: null, tem_datajud: false, classe_oficial: null }],
  site_status: { generated_at: '2026-04-01T12:00:00Z', sources: { djen: { zips_archived: 1, pairs_total: 3, tribunals_with_data: 1, tribunals_total: 1, coverage_pct: 33.3, earliest_tracked_date: '2026-04-01', earliest_upload_date: '2026-04-01', latest_upload_date: '2026-04-01', absent_confirmed: 1, pending_real: 1, errors_transient: 0, never_checked: 0, last_attempt_at: '2026-04-01T12:00:00Z', last_success_at: '2026-04-01T12:00:00Z' } } },
  stats_coverage: { avg_coverage: 50, best_count: 2, best_day: '2026-04-01', worst_count: 1, worst_day: '2026-04-02' },
  stj_relatores: [{ ministroRelator: null, total: 1 }],
  stj_temas: [{ tema: null, total: 1 }],
  stj_totals: { total: 1, total_temas: 1, ultima_decisao: '2026-04-01' },
  totals: { total: 3, uploaded: 1, pending: 1, absent: 1, unknown: 0, coverage_pct: 33.3, tribunals_total: 1, tribunals_with_data: 1 },
  tribunal_calendar: [{ tribunal: 'TJSP', date: '2026-04-01', status: 'uploaded' }],
  tribunal_coverage: [{ tribunal: 'TJSP', uploaded: 1, pending: 1, absent: 1, unknown: 0, total: 3, coverage_pct: 33.3, earliest_upload: '2026-04-01', latest_upload: '2026-04-01' }],
  weekly_pattern: [{ day_idx: 3, name: 'Qua', avg: 1, days_count: 1 }],
} satisfies Record<ContractName, unknown>;
