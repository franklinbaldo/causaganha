/**
 * Helpers puros para a página /processo — dossiê unificado de um número CNJ,
 * consultado inteiramente client-side via DuckDB-WASM contra os parquets
 * `processos_unificados.parquet` e `processo_documentos.parquet` do item IA
 * `causaganha-dashboard` (produzidos por scripts/reconcile_processos.py).
 *
 * Mantidos fora do componente Svelte para serem testáveis sem montar UI —
 * normalização de CNJ, parsing/serialização da URL compartilhável, geração
 * de SQL parametrizado e conversão de linhas cruas (Arrow → objeto simples)
 * em modelos de visualização tipados.
 */

export const IA_DASHBOARD_BASE = 'https://archive.org/download/causaganha-dashboard';
export const PROCESSOS_UNIFICADOS_URL = `${IA_DASHBOARD_BASE}/processos_unificados.parquet`;
export const PROCESSO_DOCUMENTOS_URL = `${IA_DASHBOARD_BASE}/processo_documentos.parquet`;

export const DOCUMENTOS_PAGE_SIZE = 20;

export type Fonte = 'djen' | 'juris' | 'stj' | 'datajud';
export const ALL_FONTES: readonly Fonte[] = ['djen', 'juris', 'stj', 'datajud'];

export const FONTE_LABELS: Record<Fonte, string> = {
  djen: 'DJEN',
  juris: 'JURIS (TJRO)',
  stj: 'STJ',
  datajud: 'DataJud',
};

// ── Normalização de CNJ ─────────────────────────────────────────────────────

/** Remove tudo que não for dígito. Não valida o comprimento — use isValidCnj. */
export function stripCnjMask(input: string): string {
  return (input ?? '').replace(/\D/g, '');
}

/** 20 dígitos exatos — mesma regra de scripts/reconcile_processos.py:normalizar_cnj. */
export function isValidCnj(digits: string): boolean {
  return /^\d{20}$/.test(digits);
}

/** Normaliza uma entrada de usuário (com ou sem máscara) para 20 dígitos, ou '' se inválida. */
export function normalizeCnj(input: string): string {
  const digits = stripCnjMask(input);
  return isValidCnj(digits) ? digits : '';
}

/** 20 dígitos → NNNNNNN-DD.AAAA.J.TR.OOOO — mesma máscara de scripts/reconcile_processos.py:formatar_cnj. */
export function formatCnj(digits: string): string {
  if (!isValidCnj(digits)) return digits;
  return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
}

export type CnjInputStatus = 'empty' | 'invalid' | 'valid';

/** Classifica uma entrada de busca sem decidir a mensagem — o componente decide o texto. */
export function classifyCnjInput(raw: string): CnjInputStatus {
  const trimmed = (raw ?? '').trim();
  if (!trimmed) return 'empty';
  return isValidCnj(stripCnjMask(trimmed)) ? 'valid' : 'invalid';
}

/**
 * Decide para onde a busca da home deve ir: um CNJ válido tem o dossiê
 * reconciliado (DJEN + JURIS + STJ + DataJud) em /processo, mais completo do
 * que a busca DJEN-only de /publicacoes. Retorna a URL de redirecionamento,
 * ou null quando a entrada não é um CNJ válido — nesse caso o chamador deixa
 * o formulário seguir o fluxo padrão (GET para /publicacoes).
 */
export function buildHeroSearchRedirect(raw: string, processoHref: string): string | null {
  if (classifyCnjInput(raw) !== 'valid') return null;
  const digits = normalizeCnj(raw);
  return `${processoHref}?cnj=${encodeURIComponent(formatCnj(digits))}`;
}

// ── URL compartilhável (?cnj=...) ──────────────────────────────────────────

const CNJ_PARAM = 'cnj';

/** Lê ?cnj= de uma query string bruta (ex.: window.location.search). Não normaliza. */
export function readCnjParam(search: string): string | null {
  const params = new URLSearchParams(search);
  const value = params.get(CNJ_PARAM);
  return value && value.trim() ? value : null;
}

/**
 * Nova query string com ?cnj=<mascarado>, preservando os demais parâmetros.
 * `digits` inválido remove o parâmetro em vez de gravar um valor incoerente.
 */
export function buildCnjSearchParams(search: string, digits: string): string {
  const params = new URLSearchParams(search);
  if (isValidCnj(digits)) {
    params.set(CNJ_PARAM, formatCnj(digits));
  } else {
    params.delete(CNJ_PARAM);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

// ── SQL parametrizado ───────────────────────────────────────────────────────
// Somente as colunas exibidas (nunca SELECT *); nr_processo filtrado via
// prepared statement, nunca por interpolação de string.

export function buildProcessoUnificadoSql(): string {
  return `
    SELECT
      nr_processo, nr_processo_mascara, n_fontes, fontes,
      djen_primeira_pub, djen_ultima_pub, djen_n_publicacoes, djen_tribunais,
      juris_n_documentos, juris_tipos, juris_data_julgamento,
      juris_orgao, juris_relator, juris_classe, juris_url,
      stj_id, stj_classe, stj_relator, stj_tema, stj_tese, stj_ementa,
      stj_data_decisao, stj_data_publicacao,
      classe_oficial, assuntos, orgao_julgador, grau,
      data_ajuizamento, ultima_atualizacao, tem_datajud,
      updated_at
    FROM read_parquet('${PROCESSOS_UNIFICADOS_URL}')
    WHERE nr_processo = ?
    LIMIT 1
  `;
}

/**
 * Busca `pageSize + 1` linhas a partir de `offset` — o "+1" permite detectar
 * "há mais" sem uma segunda consulta de contagem (ver paginate()).
 */
export function buildProcessoDocumentosSql(): string {
  return `
    SELECT nr_processo, fonte, id_documento, tipo, data, url, resumo
    FROM read_parquet('${PROCESSO_DOCUMENTOS_URL}')
    WHERE nr_processo = ?
    ORDER BY data DESC NULLS LAST, id_documento
    LIMIT ? OFFSET ?
  `;
}

export interface PageResult<T> {
  items: T[];
  hasMore: boolean;
}

/** rows deve ter sido buscado com LIMIT pageSize+1 (ver buildProcessoDocumentosSql). */
export function paginate<T>(rows: T[], pageSize: number): PageResult<T> {
  const hasMore = rows.length > pageSize;
  return { items: hasMore ? rows.slice(0, pageSize) : rows, hasMore };
}

// ── Conversão de valores crus (Arrow → JS) ─────────────────────────────────
// DuckDB-WASM devolve linhas Arrow; após row.toJSON() a maioria dos valores já
// é string/number/Date, mas listas e datas podem chegar como Vector/objeto
// Arrow ou string, dependendo da versão. Estas conversões são defensivas e
// puras — testáveis sem depender do runtime real do WASM.

function toStringArray(value: unknown): string[] {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed.map(String) : [value];
    } catch {
      return value.length > 0 ? [value] : [];
    }
  }
  const maybeIterable = value as { toArray?: () => unknown[]; [Symbol.iterator]?: () => Iterator<unknown> };
  if (typeof maybeIterable.toArray === 'function') return maybeIterable.toArray().map(String);
  if (typeof maybeIterable[Symbol.iterator] === 'function') return Array.from(value as Iterable<unknown>).map(String);
  return [];
}

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'bigint') return Number(value);
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toNullableString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const s = String(value);
  return s.length > 0 ? s : null;
}

/** DATE/TIMESTAMP arbitrário (Date, string ISO, epoch numérico) → 'YYYY-MM-DD', ou null. */
export function toIsoDate(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value.toISOString().slice(0, 10);
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'bigint') {
    const parsed = new Date(typeof value === 'bigint' ? Number(value) : value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString().slice(0, 10);
  }
  return null;
}

/** TIMESTAMP arbitrário → rótulo pt-BR/UTC via formatUtcDateTime, ou null. */
export function toIsoTimestampString(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value.toISOString();
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'bigint') {
    const parsed = new Date(typeof value === 'bigint' ? Number(value) : value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
  }
  return null;
}

// ── Modelos de visualização ────────────────────────────────────────────────

export interface ProcessoUnificadoRow {
  nrProcesso: string;
  nrProcessoMascara: string;
  nFontes: number;
  fontes: Fonte[];
  djen: {
    present: boolean;
    primeiraPub: string | null;
    ultimaPub: string | null;
    nPublicacoes: number | null;
    tribunais: string[];
  };
  juris: {
    present: boolean;
    nDocumentos: number | null;
    tipos: string[];
    dataJulgamento: string | null;
    orgao: string | null;
    relator: string | null;
    classe: string | null;
    url: string | null;
  };
  stj: {
    present: boolean;
    id: string | null;
    classe: string | null;
    relator: string | null;
    tema: string | null;
    tese: string | null;
    ementa: string | null;
    dataDecisao: string | null;
    dataPublicacao: string | null;
  };
  datajud: {
    present: boolean;
    classeOficial: string | null;
    assuntos: string | null;
    orgaoJulgador: string | null;
    grau: string | null;
    dataAjuizamento: string | null;
    ultimaAtualizacao: string | null;
  };
  /** ISO cru (para testes/derivações); use datasetGeneratedAtLabel() para exibir. */
  updatedAtRaw: string | null;
}

/** Converte uma linha crua (raw.<coluna> de processos_unificados) no modelo de visualização. */
export function mapProcessoRow(raw: Record<string, unknown>): ProcessoUnificadoRow {
  const fontes = toStringArray(raw.fontes) as Fonte[];
  const has = (f: Fonte) => fontes.includes(f);
  const nrProcesso = String(raw.nr_processo ?? '');

  return {
    nrProcesso,
    nrProcessoMascara: toNullableString(raw.nr_processo_mascara) ?? formatCnj(nrProcesso),
    nFontes: toNumber(raw.n_fontes) ?? fontes.length,
    fontes,
    djen: {
      present: has('djen'),
      primeiraPub: toIsoDate(raw.djen_primeira_pub),
      ultimaPub: toIsoDate(raw.djen_ultima_pub),
      nPublicacoes: toNumber(raw.djen_n_publicacoes),
      tribunais: toStringArray(raw.djen_tribunais),
    },
    juris: {
      present: has('juris'),
      nDocumentos: toNumber(raw.juris_n_documentos),
      tipos: toStringArray(raw.juris_tipos),
      dataJulgamento: toIsoDate(raw.juris_data_julgamento),
      orgao: toNullableString(raw.juris_orgao),
      relator: toNullableString(raw.juris_relator),
      classe: toNullableString(raw.juris_classe),
      url: toNullableString(raw.juris_url),
    },
    stj: {
      present: has('stj'),
      id: toNullableString(raw.stj_id),
      classe: toNullableString(raw.stj_classe),
      relator: toNullableString(raw.stj_relator),
      tema: toNullableString(raw.stj_tema),
      tese: toNullableString(raw.stj_tese),
      ementa: toNullableString(raw.stj_ementa),
      dataDecisao: toIsoDate(raw.stj_data_decisao),
      dataPublicacao: toIsoDate(raw.stj_data_publicacao),
    },
    datajud: {
      // tem_datajud é a fonte da verdade (RFC 0010) — 'datajud' em fontes
      // acompanha o mesmo booleano, então checar os dois é redundante mas
      // inofensivo caso um dia divirjam.
      present: has('datajud') && Boolean(raw.tem_datajud),
      classeOficial: toNullableString(raw.classe_oficial),
      assuntos: toNullableString(raw.assuntos),
      orgaoJulgador: toNullableString(raw.orgao_julgador),
      grau: toNullableString(raw.grau),
      dataAjuizamento: toIsoDate(raw.data_ajuizamento),
      ultimaAtualizacao: toIsoDate(raw.ultima_atualizacao),
    },
    updatedAtRaw: toIsoTimestampString(raw.updated_at),
  };
}

export interface ProcessoDocumentoRow {
  fonte: Fonte | string;
  idDocumento: string;
  tipo: string | null;
  data: string | null;
  url: string | null;
  resumo: string | null;
}

/** Converte uma linha crua de processo_documentos no modelo de visualização. */
export function mapDocumentoRow(raw: Record<string, unknown>): ProcessoDocumentoRow {
  return {
    fonte: String(raw.fonte ?? ''),
    idDocumento: String(raw.id_documento ?? ''),
    tipo: toNullableString(raw.tipo),
    data: toIsoDate(raw.data),
    url: toNullableString(raw.url),
    resumo: toNullableString(raw.resumo),
  };
}

export interface Completude {
  presentes: Fonte[];
  ausentes: Fonte[];
  pct: number;
}

/** Grau de completude: quantas das 4 fontes possíveis contribuíram para este CNJ. */
export function completude(fontes: Fonte[]): Completude {
  const presentes = ALL_FONTES.filter((f) => fontes.includes(f));
  const ausentes = ALL_FONTES.filter((f) => !fontes.includes(f));
  return { presentes, ausentes, pct: Math.round((presentes.length / ALL_FONTES.length) * 100) };
}

/** "Processo localizado, mas sem documentos associados" — distinto de "não encontrado". */
export function isDocumentosVazio(items: unknown[], offset: number): boolean {
  return offset === 0 && items.length === 0;
}
