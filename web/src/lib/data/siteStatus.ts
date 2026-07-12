/**
 * Loader do artefato canônico de status do site (data/site-status.json,
 * contrato `site_status` — ver web/src/queries/site_status.qmd).
 *
 * Diferente dos demais contratos (arquivo ausente → null → EmptyState), o
 * site-status é OBRIGATÓRIO: ele alimenta os números globais da homepage e
 * das páginas de dados, e um build sem ele publicaria um site que mente sobre
 * o próprio acervo. Por isso `loadSiteStatus()`:
 *
 *  - lança erro (falha o build Astro) quando o JSON está ausente;
 *  - lança erro quando `generated_at` está ausente/inválido ou é mais antigo
 *    que STALE_BUILD_LIMIT_MS (7 dias) — deploy honesto: melhor falhar do que
 *    publicar métricas de uma safra antiga.
 *
 * Semântica de frescor por fonte (limiar de 48h, calculado no render — ver o
 * .qmd): 'atualizado' | 'atrasado' | 'desconhecido'. O valor 'indisponivel' é
 * reservado ao frontend para fontes sem artefato.
 */
import { loadContractBuildTime } from './index';
import type { SiteStatus, SiteStatusFreshness } from './contracts';

/** Build recusa um site-status.json mais velho que isto (7 dias). */
export const STALE_BUILD_LIMIT_MS = 7 * 24 * 60 * 60 * 1000;

/** Rótulos de exibição (pt-BR) para o estado de frescor por fonte. */
export const FRESHNESS_LABELS: Record<SiteStatusFreshness, string> = {
  atualizado: 'Atualizado',
  atrasado: 'Atrasado',
  indisponivel: 'Indisponível',
  desconhecido: 'Desconhecido',
};

const HINT =
  'Rode `uv run python scripts/render_queries.py` (deploy-web.yml usa --strict) ' +
  'antes de `npm run build`.';

/**
 * Carrega e valida o site-status em tempo de build. Nunca retorna null:
 * ausência ou obsolescência é falha de build (não EmptyState).
 */
export async function loadSiteStatus(publicDir?: string): Promise<SiteStatus> {
  const status = await loadContractBuildTime('site_status', publicDir);
  if (!status) {
    throw new Error(
      `site-status.json ausente (contrato obrigatório "site_status"). ${HINT}`,
    );
  }
  const generated = Date.parse(status.generated_at);
  if (!Number.isFinite(generated)) {
    throw new Error(
      `site-status.json com generated_at inválido: ${JSON.stringify(status.generated_at)}. ${HINT}`,
    );
  }
  const age = Date.now() - generated;
  if (age > STALE_BUILD_LIMIT_MS) {
    const days = (age / 86_400_000).toFixed(1);
    throw new Error(
      `site-status.json obsoleto: gerado há ${days} dias (limite: 7). ` +
        `Recuse-se a publicar métricas velhas — regenere o artefato. ${HINT}`,
    );
  }
  return status;
}
