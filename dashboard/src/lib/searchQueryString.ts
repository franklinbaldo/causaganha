import type { DjenComunicacaoQuery } from "./djen";

export type SmartParseKind = "processo" | "oab" | "texto";

export interface SmartParseResult {
  kind: SmartParseKind;
  patch: Partial<DjenComunicacaoQuery>;
  label: string;
}

// CNJ process numbers are 20 digits: NNNNNNN-DD.AAAA.J.TR.OOOO.
// Accept masked, partially masked or unmasked variants.
const CNJ_MASKED_RE = /^\s*\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\s*$/;
const CNJ_BARE_RE = /^\s*\d{20}\s*$/;

// OAB formats: "OAB/SP 123456", "OAB SP 123456", "SP 123456", "SP-123456".
const OAB_RE = /^\s*(?:OAB\s*[/-]?\s*)?([A-Za-z]{2})\s*[-/ ]?\s*(\d{3,6})\s*$/;

export function smartParseInput(raw: string): SmartParseResult {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { kind: "texto", patch: {}, label: "" };
  }

  if (CNJ_MASKED_RE.test(trimmed) || CNJ_BARE_RE.test(trimmed)) {
    const digits = trimmed.replace(/\D/g, "");
    return {
      kind: "processo",
      patch: { numeroProcesso: digits },
      label: "Número de processo CNJ detectado",
    };
  }

  const oabMatch = trimmed.match(OAB_RE);
  if (oabMatch) {
    const uf = oabMatch[1].toUpperCase();
    const numero = oabMatch[2];
    return {
      kind: "oab",
      patch: { ufOab: uf, numeroOab: numero },
      label: `OAB ${uf}/${numero} detectada`,
    };
  }

  return {
    kind: "texto",
    patch: { texto: trimmed },
    label: "Busca textual",
  };
}

const URL_SYNC_KEYS: readonly string[] = [
  "numeroOab",
  "ufOab",
  "nomeAdvogado",
  "nomeParte",
  "numeroProcesso",
  "dataDisponibilizacaoInicio",
  "dataDisponibilizacaoFim",
  "siglaTribunal",
  "pagina",
  "itensPorPagina",
  "meio",
  "texto",
];

const NUMERIC_KEYS = new Set<string>(["pagina", "itensPorPagina"]);

export function queryToSearchParams(q: DjenComunicacaoQuery): URLSearchParams {
  const params = new URLSearchParams();
  const source = q as Record<string, unknown>;
  for (const key of URL_SYNC_KEYS) {
    const value = source[key];
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  return params;
}

export function searchParamsToQuery(sp: URLSearchParams): DjenComunicacaoQuery {
  const out: Record<string, unknown> = {};
  for (const key of URL_SYNC_KEYS) {
    const value = sp.get(key);
    if (value === null || value === "") continue;
    if (NUMERIC_KEYS.has(key)) {
      const asNumber = Number(value);
      if (Number.isFinite(asNumber)) {
        out[key] = asNumber;
      }
      continue;
    }
    out[key] = value;
  }
  return out as DjenComunicacaoQuery;
}

export function pushQueryToUrl(q: DjenComunicacaoQuery): void {
  if (typeof window === "undefined") return;
  const params = queryToSearchParams(q);
  const qs = params.toString();
  const url = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash}`;
  window.history.replaceState({}, "", url);
}

export function hasAnyQueryValue(q: DjenComunicacaoQuery): boolean {
  const source = q as Record<string, unknown>;
  for (const key of URL_SYNC_KEYS) {
    const value = source[key];
    if (value !== undefined && value !== null && value !== "") return true;
  }
  return false;
}
