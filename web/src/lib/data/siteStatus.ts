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
 *  - lança erro quando `generated_at` está ausente/inválido, é mais antigo
 *    que STALE_BUILD_LIMIT_MS (7 dias) — deploy honesto: melhor falhar do que
 *    publicar métricas de uma safra antiga — ou está mais de
 *    MAX_FUTURE_SKEW_MS (5 min) no futuro (relógio quebrado no render).
 *
 * Frescor por fonte: derivado AQUI (não no SQL) a partir de
 * `last_success_at` — o timestamp da última tentativa CONCLUSIVA (upload
 * confirmado ou veredito DJEN). `last_attempt_at` muda em qualquer resposta,
 * inclusive 403/timeout, então um bot falhando continuamente mantém
 * `last_attempt_at` fresco sem mover `last_success_at`; esse estado aparece
 * como "Atrasado — tentativas recentes falhando" (failingRecently).
 *
 * Todos os helpers de tempo recebem `now` como parâmetro (sem Date.now()
 * interno) para serem puros e testáveis — ver siteStatus.test.ts.
 */
import { loadContractBuildTime } from './index';
import type { SiteStatus, SiteStatusSource } from './contracts';

/** Estado de frescor de uma fonte (derivado no build, nunca lido do JSON). */
export type SiteStatusFreshness =
  | 'atualizado'
  | 'atrasado'
  | 'indisponivel'
  | 'desconhecido';

/** Build recusa um site-status.json mais velho que isto (7 dias). */
export const STALE_BUILD_LIMIT_MS = 7 * 24 * 60 * 60 * 1000;

/** Build recusa um generated_at mais de 5 min no futuro (clock skew). */
export const MAX_FUTURE_SKEW_MS = 5 * 60 * 1000;

/** Fonte é 'atualizado' quando o último SUCESSO tem ≤ 48h. */
export const FRESHNESS_THRESHOLD_MS = 48 * 60 * 60 * 1000;

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
 * Epoch ms de um timestamp ISO, ou null quando ausente/imparseável.
 * Nunca deixa um "Invalid Date" vazar para a UI.
 */
export function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  const ms = Date.parse(value);
  return Number.isFinite(ms) ? ms : null;
}

/**
 * Formata um timestamp ISO como data/hora UTC pt-BR para exibição.
 * Ausente ou imparseável → null (o chamador exibe um fallback explícito,
 * nunca "Invalid Date UTC").
 */
export function formatUtcDateTime(value: string | null | undefined): string | null {
  const ms = parseTimestamp(value);
  if (ms === null) return null;
  return (
    new Date(ms).toLocaleString('pt-BR', {
      timeZone: 'UTC',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }) + ' UTC'
  );
}

/**
 * Valida generated_at contra o relógio `now` (epoch ms). Lança erro quando
 * ausente/inválido, mais velho que STALE_BUILD_LIMIT_MS ou mais de
 * MAX_FUTURE_SKEW_MS no futuro. Puro: não lê Date.now().
 */
export function assertGeneratedAtAcceptable(
  generatedAt: string | null | undefined,
  now: number,
): void {
  const generated = parseTimestamp(generatedAt);
  if (generated === null) {
    throw new Error(
      `site-status.json com generated_at inválido: ${JSON.stringify(generatedAt)}. ${HINT}`,
    );
  }
  const age = now - generated;
  if (age > STALE_BUILD_LIMIT_MS) {
    const days = (age / 86_400_000).toFixed(1);
    throw new Error(
      `site-status.json obsoleto: gerado há ${days} dias (limite: 7). ` +
        `Recuse-se a publicar métricas velhas — regenere o artefato. ${HINT}`,
    );
  }
  if (age < -MAX_FUTURE_SKEW_MS) {
    const minutes = (-age / 60_000).toFixed(1);
    throw new Error(
      `site-status.json vindo do futuro: generated_at ${minutes} min à frente ` +
        `do relógio do build (tolerância: 5 min). Relógio do render ou do build ` +
        `está errado — não publique métricas com carimbo suspeito. ${HINT}`,
    );
  }
}

/** Resultado da avaliação de frescor de uma fonte. */
export interface SourceFreshness {
  freshness: SiteStatusFreshness;
  /**
   * true quando a fonte está 'atrasado' mas houve tentativa recente (≤ 48h):
   * o bot está ativo porém falhando — estado que merece destaque na UI.
   */
  failingRecently: boolean;
}

/**
 * Deriva o frescor de uma fonte a partir de last_success_at/last_attempt_at.
 * Regras (limiar FRESHNESS_THRESHOLD_MS = 48h, relativo a `now`):
 *
 *  - sucesso ≤ 48h            → 'atualizado'
 *  - sucesso > 48h (ou nunca, mas com tentativas registradas) → 'atrasado'
 *  - nenhum timestamp válido  → 'desconhecido'
 *
 * Timestamps no futuro além de MAX_FUTURE_SKEW_MS nunca contam como
 * recentes: a guarda de skew do generated_at não cobre os timestamps
 * por-fonte, então um last_success_at absurdamente futuro renderizaria
 * 'atualizado' para sempre sem esta checagem.
 *
 * `failingRecently` marca o caso "atrasado com atividade recente": tentativa
 * ≤ 48h mas sem sucesso ≤ 48h — falha contínua, jamais 'atualizado'.
 */
export function evaluateSourceFreshness(
  source: Pick<SiteStatusSource, 'last_attempt_at' | 'last_success_at'>,
  now: number,
): SourceFreshness {
  const success = parseTimestamp(source.last_success_at);
  const attempt = parseTimestamp(source.last_attempt_at);

  if (success === null && attempt === null) {
    return { freshness: 'desconhecido', failingRecently: false };
  }
  const isRecent = (ts: number): boolean => {
    const age = now - ts;
    return age >= -MAX_FUTURE_SKEW_MS && age <= FRESHNESS_THRESHOLD_MS;
  };
  if (success !== null && isRecent(success)) {
    return { freshness: 'atualizado', failingRecently: false };
  }
  const attemptRecent = attempt !== null && isRecent(attempt);
  return { freshness: 'atrasado', failingRecently: attemptRecent };
}

/**
 * Rótulo de exibição do frescor; o estado "atrasado com tentativas recentes
 * falhando" ganha um rótulo próprio para que falha contínua seja legível.
 */
export function freshnessDisplayLabel(sf: SourceFreshness): string {
  if (sf.freshness === 'atrasado' && sf.failingRecently) {
    return 'Atrasado — tentativas recentes falhando';
  }
  return FRESHNESS_LABELS[sf.freshness];
}

/**
 * Fração de `value` sobre `total` em porcentagem, com guarda de divisão por
 * zero: total ≤ 0 → 0 (nunca NaN/Infinity na página).
 */
export function pctOfTotal(value: number, total: number): number {
  return total > 0 ? (value / total) * 100 : 0;
}

/**
 * Carrega e valida o site-status em tempo de build. Nunca retorna null:
 * ausência, obsolescência ou carimbo futuro é falha de build (não EmptyState).
 *
 * @param publicDir base dos JSONs renderizados (default `./public`).
 * @param now relógio de referência em epoch ms (default `Date.now()`) —
 *   injetável para testes.
 */
export async function loadSiteStatus(
  publicDir?: string,
  now: number = Date.now(),
): Promise<SiteStatus> {
  const status = await loadContractBuildTime('site_status', publicDir);
  if (!status) {
    throw new Error(
      `site-status.json ausente (contrato obrigatório "site_status"). ${HINT}`,
    );
  }
  assertGeneratedAtAcceptable(status.generated_at, now);
  return status;
}
