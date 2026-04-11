/**
 * DJEN public-facing module.
 *
 * This file used to hand-write ~200 lines of Zod schemas that replicated
 * `djen.yml`. Those schemas have been replaced by types generated directly
 * from the spec (`djen-types.gen.ts`) and consumed by the typed HTTP client
 * in `djenClient.ts`. What remains here is the runtime knowledge the spec
 * does NOT capture:
 *
 *   - Date normalization (`dd/MM/yyyy` ↔ `YYYY-MM-DD`)
 *   - Enum coercion for `meio` and `polo` (the live API mixes codes, words
 *     and accented spellings)
 *   - HTML sanitization for the `texto` body
 *   - camelCase/snake_case unification for field names the live API is
 *     inconsistent about (`siglaTribunal` vs `sigla_tribunal` etc.)
 *
 * The module also exposes a backward-compatible `searchDjenComunicacoes`
 * entry point so the component layer (`PublicationSearch.svelte`) and the
 * BDD step tests keep working.
 */

import DOMPurify from "dompurify";
import {
  DjenRateLimitError,
  DjenValidationError,
  _resetGeoState,
  searchComunicacoes,
  type DjenCallResult,
  type DjenComunicacaoItem,
  type DjenComunicacaoQuery,
  type DjenRateLimit,
  type DjenSearchPayload,
} from "./djenClient";

// ---------- re-exports ------------------------------------------------------

export {
  DjenRateLimitError,
  DjenValidationError,
  type DjenComunicacaoQuery,
  type DjenRateLimit,
};

// ---------- normalized public type -----------------------------------------

export type DjenMeio = "D" | "E";
export type DjenPolo = "A" | "P" | "T" | "D";

export type DjenTextoRender =
  | { kind: "html"; content: string }
  | { kind: "text"; content: string };

export interface DjenDestinatario {
  nome?: string;
  polo?: DjenPolo;
  comunicacao_id?: number;
  cpf_cnpj?: string;
  [key: string]: unknown;
}

export interface DjenAdvogado {
  id?: number;
  nome?: string;
  numero_oab?: string;
  uf_oab?: string;
  tipo_inscricao?: string;
  email?: string;
  [key: string]: unknown;
}

export interface DjenDestinatarioAdvogado {
  id?: number;
  comunicacao_id?: number;
  advogado_id?: number;
  created_at?: string;
  updated_at?: string;
  advogado?: DjenAdvogado;
  [key: string]: unknown;
}

export interface DjenPublication {
  id?: number;
  data_disponibilizacao?: string;
  siglaTribunal?: string;
  tipoComunicacao?: string;
  nomeOrgao?: string;
  idOrgao?: number;
  texto?: string;
  numero_processo?: string;
  meio?: DjenMeio;
  link?: string;
  tipoDocumento?: string;
  nomeClasse?: string;
  codigoClasse?: string;
  numeroComunicacao?: number;
  ativo?: boolean;
  hash?: string;
  status?: string;
  motivo_cancelamento?: string;
  data_cancelamento?: string;
  meiocompleto?: string;
  numeroprocessocommascara?: string;
  destinatarios?: DjenDestinatario[];
  destinatarioadvogados?: DjenDestinatarioAdvogado[];
  textoRender?: DjenTextoRender;
  [key: string]: unknown;
}

// ---------- low-level transforms (kept from the old implementation) -------

function normalizeLabel(value: unknown): string {
  return (typeof value === "string" ? value : String(value))
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function normalizeDateString(value: unknown): string | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const raw = typeof value === "string" ? value.trim() : String(value).trim();
  if (!raw) return undefined;

  const isoDateMatch = raw.match(/^(\d{4}-\d{2}-\d{2})/);
  if (isoDateMatch) return isoDateMatch[1];

  const brDateMatch = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brDateMatch) {
    const [, day, month, year] = brDateMatch;
    return `${year}-${month}-${day}`;
  }

  const dashedBrDateMatch = raw.match(/^(\d{2})-(\d{2})-(\d{4})$/);
  if (dashedBrDateMatch) {
    const [, day, month, year] = dashedBrDateMatch;
    return `${year}-${month}-${day}`;
  }

  return raw;
}

export function normalizeMeio(value: unknown): DjenMeio | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const raw = normalizeLabel(value);
  if (!raw) return undefined;

  if (
    raw === "d" ||
    raw === "diario" ||
    raw === "diario eletronico" ||
    raw === "eletronico" ||
    raw === "eletronico nacional"
  ) {
    return "D";
  }
  if (raw === "e" || raw === "edital" || raw === "edital eletronico") {
    return "E";
  }
  return undefined;
}

export function normalizePolo(value: unknown): DjenPolo | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const raw = normalizeLabel(value);
  if (!raw) return undefined;

  if (
    raw === "a" ||
    raw === "ativo" ||
    raw === "ativa" ||
    raw === "autor" ||
    raw === "autora"
  ) {
    return "A";
  }
  if (raw === "p" || raw === "passivo" || raw === "passiva" || raw === "reu" || raw === "re") {
    return "P";
  }
  if (raw === "t" || raw === "terceiro" || raw === "terceira") {
    return "T";
  }
  if (raw === "d" || raw === "destinatario") {
    return "D";
  }
  return undefined;
}

function looksLikeHtml(value: string): boolean {
  return /<\/?[a-z][\s\S]*>/i.test(value);
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function sanitizeHtml(value: string): string {
  if (typeof window === "undefined") return escapeHtml(value);
  return DOMPurify.sanitize(value, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["script", "style"],
    FORBID_ATTR: ["style"],
  });
}

export function normalizeExternalUrl(value: unknown): string | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const raw = typeof value === "string" ? value.trim() : String(value).trim();
  if (!raw) return undefined;

  try {
    const url = new URL(raw);
    if (url.protocol === "http:" || url.protocol === "https:") {
      return url.toString();
    }
  } catch {
    return undefined;
  }
  return undefined;
}

// ---------- publication normalization -------------------------------------

/**
 * Convert one raw comunicacao item (as returned by the DJEN API, possibly
 * with the snake_case / camelCase mix the spec doesn't capture) into the
 * canonical shape consumed by the UI.
 */
export function normalizePublication(
  raw: DjenComunicacaoItem & Record<string, unknown>,
): DjenPublication {
  const pub: DjenPublication = { ...(raw as Record<string, unknown>) };

  const dataDisponibilizacao =
    (raw as Record<string, unknown>).data_disponibilizacao ??
    (raw as Record<string, unknown>).datadisponibilizacao ??
    (raw as Record<string, unknown>).dataDisponibilizacao;
  pub.data_disponibilizacao = normalizeDateString(dataDisponibilizacao);

  pub.siglaTribunal =
    ((raw as Record<string, unknown>).siglaTribunal as string | undefined) ??
    ((raw as Record<string, unknown>).sigla_tribunal as string | undefined);

  pub.tipoComunicacao =
    ((raw as Record<string, unknown>).tipoComunicacao as string | undefined) ??
    ((raw as Record<string, unknown>).tipo_comunicacao as string | undefined);

  pub.nomeOrgao =
    ((raw as Record<string, unknown>).nomeOrgao as string | undefined) ??
    ((raw as Record<string, unknown>).nome_orgao as string | undefined) ??
    ((raw as Record<string, unknown>).orgao as string | undefined);

  const idOrgaoValue =
    (raw as Record<string, unknown>).idOrgao ?? (raw as Record<string, unknown>).id_orgao;
  pub.idOrgao = typeof idOrgaoValue === "number" ? idOrgaoValue : undefined;

  pub.numero_processo =
    ((raw as Record<string, unknown>).numero_processo as string | undefined) ??
    ((raw as Record<string, unknown>).numeroProcesso as string | undefined);

  pub.meio = normalizeMeio((raw as Record<string, unknown>).meio);
  pub.link = normalizeExternalUrl((raw as Record<string, unknown>).link);

  pub.tipoDocumento =
    ((raw as Record<string, unknown>).tipoDocumento as string | undefined) ??
    ((raw as Record<string, unknown>).tipo_documento as string | undefined);

  pub.nomeClasse =
    ((raw as Record<string, unknown>).nomeClasse as string | undefined) ??
    ((raw as Record<string, unknown>).nome_classe as string | undefined);

  pub.codigoClasse =
    ((raw as Record<string, unknown>).codigoClasse as string | undefined) ??
    ((raw as Record<string, unknown>).codigo_classe as string | undefined);

  const numeroComunicacaoValue =
    (raw as Record<string, unknown>).numeroComunicacao ??
    (raw as Record<string, unknown>).numero_comunicacao;
  pub.numeroComunicacao =
    typeof numeroComunicacaoValue === "number" ? numeroComunicacaoValue : undefined;

  if (typeof raw.texto === "string" && raw.texto.length > 0) {
    pub.textoRender = looksLikeHtml(raw.texto)
      ? { kind: "html", content: sanitizeHtml(raw.texto) }
      : { kind: "text", content: raw.texto };
  }

  if (Array.isArray((raw as Record<string, unknown>).destinatarios)) {
    pub.destinatarios = (
      (raw as Record<string, unknown>).destinatarios as Array<Record<string, unknown>>
    ).map((d) => ({
      ...d,
      nome: typeof d.nome === "string" ? d.nome : undefined,
      polo: normalizePolo(d.polo),
      comunicacao_id:
        typeof d.comunicacao_id === "number" ? d.comunicacao_id : undefined,
      cpf_cnpj: typeof d.cpf_cnpj === "string" ? d.cpf_cnpj : undefined,
    }));
  }

  return pub;
}

// ---------- backward-compatible public API --------------------------------

export interface DjenSearchResult {
  items: DjenPublication[];
  count: number;
  rateLimit: DjenRateLimit;
  source: "djen";
  usedFallback: boolean;
}

const DJEN_IDENTITY_KEYS = [
  "siglaTribunal",
  "texto",
  "nomeParte",
  "nomeAdvogado",
  "numeroOab",
  "numeroProcesso",
] as const;

function hasIdentityParam(query: DjenComunicacaoQuery): boolean {
  return DJEN_IDENTITY_KEYS.some((key) => {
    const value = (query as Record<string, unknown>)[key];
    return typeof value === "string" && value.trim().length > 0;
  });
}

/**
 * Backward-compatible entry point used by `PublicationSearch.svelte` and the
 * BDD step tests. Thin wrapper around `djenClient.searchComunicacoes` that:
 *   1. Enforces the CNJ "you must provide an identity parameter OR a small
 *      page" rule before firing any request.
 *   2. Normalizes every item via `normalizePublication`.
 *   3. Preserves the `{ items, count, rateLimit, source, usedFallback }`
 *      shape the components already consume.
 */
export async function searchDjenComunicacoes(
  query: DjenComunicacaoQuery,
  opts: { signal?: AbortSignal; bypassCache?: boolean } = {},
): Promise<DjenSearchResult> {
  const smallPage =
    typeof query.itensPorPagina === "number" &&
    query.itensPorPagina > 0 &&
    query.itensPorPagina <= 5;

  if (!hasIdentityParam(query) && !smallPage) {
    throw new DjenValidationError([
      "Informe ao menos um de: tribunal, texto, parte, advogado, OAB ou processo.",
    ]);
  }

  // The `bypassCache` flag is preserved for API compatibility but the
  // library-level LRU cache is gone — TanStack Query now owns all caching
  // behavior at the component layer. We therefore honor the signature
  // without doing any caching work ourselves.
  void opts.bypassCache;

  const result: DjenCallResult<DjenSearchPayload> = await searchComunicacoes(query, {
    signal: opts.signal,
  });

  return {
    items: result.data.items.map((raw) =>
      normalizePublication(raw as DjenComunicacaoItem & Record<string, unknown>),
    ),
    count: result.data.count,
    rateLimit: result.rateLimit,
    source: "djen",
    usedFallback: result.usedFallback,
  };
}

/**
 * Fetch the live detail for a publication that was originally loaded from an
 * Internet Archive snapshot. The DateDetail component uses this to "hydrate"
 * a card with the latest DJEN content when the user lands on the date page.
 */
export async function fetchLivePublicationDetail(
  pubFromIa: DjenPublication,
  opts: { signal?: AbortSignal } = {},
): Promise<{
  publication: DjenPublication | null;
  source: "djen" | "ia";
  usedFallback: boolean;
  error?: string;
}> {
  if (!pubFromIa.numeroComunicacao || !pubFromIa.siglaTribunal) {
    return {
      publication: pubFromIa,
      source: "ia",
      usedFallback: true,
      error: "Missing identity fields",
    };
  }

  try {
    const result = await searchComunicacoes(
      {
        numeroComunicacao: pubFromIa.numeroComunicacao,
        siglaTribunal: pubFromIa.siglaTribunal,
      },
      { signal: opts.signal },
    );
    const first = result.data.items[0];
    if (first) {
      return {
        publication: normalizePublication(
          first as DjenComunicacaoItem & Record<string, unknown>,
        ),
        source: "djen",
        usedFallback: result.usedFallback,
      };
    }
    return { publication: pubFromIa, source: "ia", usedFallback: true };
  } catch (err) {
    if (err instanceof DjenRateLimitError) {
      throw err;
    }
    return {
      publication: pubFromIa,
      source: "ia",
      usedFallback: true,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

/**
 * Reset DJEN client state. With the library-level cache removed, this now
 * only resets the geo-fence state machine, which is exactly what the BDD
 * step tests need between runs.
 */
export function clearDjenSearchCache(): void {
  _resetGeoState();
}
