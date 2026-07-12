/**
 * Seleção canônica dos tribunais exibidos na área Advogados/OAB.
 *
 * Fonte única: contrato `tribunal_coverage` (renderizado do manifesto
 * canônico sync-manifest.parquet). Substitui o snapshot legado
 * `cache/backfill.json`, cujo `data_rate_pct` vinha de um caminho paralelo e
 * podia divergir de `days_with_data`/`days_total` (ex.: "0 de 0 dias" ao lado
 * de 76% de cobertura). Aqui os três números saem da MESMA linha do contrato:
 *
 *   - daysWithData = uploaded  (dias tribunal × dia com ZIP no IA)
 *   - daysTotal    = total     (dias rastreados no manifesto)
 *   - dataRatePct  = coverage_pct (= 100 * uploaded / total, calculado no SQL)
 *
 * Usado por advogados.astro, advogados/[tribunal].astro (getStaticPaths) e
 * sitemap.xml.ts — a lista de rotas geradas e a lista exibida/indexada são,
 * por construção, a mesma.
 *
 * LIMITAÇÃO CONHECIDA: a seleção ordena por cobertura de ARQUIVO (ZIPs no
 * IA), não pela quantidade de registros de advogados/OAB processados para
 * cada tribunal — essas são tabelas diferentes. Um tribunal com ótima
 * cobertura de ZIPs pode ter poucos advogados processados, e vice-versa.
 * Enquanto o contrato não expuser métricas próprias de advogados (ex.:
 * advogados_rows, advogados_with_oab, unique_advogados), a página está
 * medindo disponibilidade de arquivo como proxy de disponibilidade de dados
 * de advogados — não são a mesma coisa.
 */
import type { TribunalCoverageRow } from './data/contracts';

export interface AdvogadosTribunalStat {
  tribunal: string;
  dataRatePct: number;
  daysWithData: number;
  daysTotal: number;
}

export const ADVOGADOS_TRIBUNALS_LIMIT = 12;

/** Top-N tribunais por cobertura de arquivo, com pelo menos um ZIP no IA. */
export function topAdvogadosTribunals(
  coverage: TribunalCoverageRow[] | null,
  limit: number = ADVOGADOS_TRIBUNALS_LIMIT,
): AdvogadosTribunalStat[] {
  return (coverage ?? [])
    .filter((row) => row.uploaded > 0)
    .map((row) => ({
      tribunal: row.tribunal.toUpperCase(),
      dataRatePct: row.coverage_pct ?? 0,
      daysWithData: row.uploaded,
      daysTotal: row.total,
    }))
    .sort(
      (a, b) =>
        b.dataRatePct - a.dataRatePct || a.tribunal.localeCompare(b.tribunal),
    )
    .slice(0, limit);
}
