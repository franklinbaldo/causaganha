/**
 * Helpers para a página /processo — dossiê unificado de um número CNJ,
 * consultado inteiramente client-side via DuckDB-WASM.
 *
 * Mesmo desenho de `causaganha/processos/service.py`: `indice_processual.parquet`
 * (item IA `causaganha-dashboard`, produzido por scripts/reconcile_processos.py)
 * só diz quais fontes (DJEN/JURIS/STJ/DataJud) têm registro para um CNJ e em
 * qual parquet cada registro vive — o dossiê em si é montado consultando os
 * parquets de origem diretamente. O índice nunca guarda cópia dos campos de
 * conteúdo.
 *
 * Funções puras (normalização de CNJ, parsing/serialização da URL
 * compartilhável, geração de SQL parametrizado, conversão de linhas cruas) e
 * a orquestração assíncrona (`buscarProcesso`/`carregarDocumentos`, que
 * recebem a conexão DuckDB-WASM já aberta) ficam aqui, fora do componente
 * Svelte, para serem testáveis sem montar UI.
 */

import { FRESHNESS_THRESHOLD_MS, parseTimestamp } from './data/siteStatus';

export const IA_DASHBOARD_BASE = 'https://archive.org/download/causaganha-dashboard';
export const INDICE_PROCESSUAL_URL = `${IA_DASHBOARD_BASE}/indice_processual.parquet`;
export const REPORT_URL = `${IA_DASHBOARD_BASE}/indice_processual.report.json`;

// Rollout fallback (RFC 0014 M2 review): indice_processual.parquet is a brand
// new artifact — deploy-web.yml can build/deploy before update-catalog.yml
// has ever published it (that step only runs when has_new_uploads==true; a
// plain push to main touching web/**/render_queries.py deploys immediately,
// with no ordering guarantee against the catalog pipeline). Without a
// fallback, /processo would regress from "has real reconciled data" (its
// state today, reading these two files) to "indisponível" for however long
// that takes. These files are frozen (the reconciler stopped writing to
// them, but nothing deletes them from IA), so they remain a valid — if
// increasingly stale — source until the index is confirmed published.
// Mirrors scripts/render_queries.py's own _comunicacoes_urls_from_catalog
// fallback. Remove once indice_processual.parquet has been confirmed
// published at least once.
export const PROCESSOS_UNIFICADOS_URL_LEGADO = `${IA_DASHBOARD_BASE}/processos_unificados.parquet`;
export const PROCESSO_DOCUMENTOS_URL_LEGADO = `${IA_DASHBOARD_BASE}/processo_documentos.parquet`;

export const DOCUMENTOS_PAGE_SIZE = 20;

export type Fonte = 'djen' | 'juris' | 'stj' | 'datajud';
export const ALL_FONTES: readonly Fonte[] = ['djen', 'juris', 'stj', 'datajud'];

export const FONTE_LABELS: Record<Fonte, string> = {
  djen: 'DJEN',
  juris: 'JURIS (TJRO)',
  stj: 'STJ',
  datajud: 'DataJud',
};

const RELATORIO_INDISPONIVEL_AVISO =
  'Relatório de cobertura (indice_processual.report.json) indisponível; sem detalhamento de ' +
  'quais fontes estavam carregadas na geração do dataset.';

// ── Normalização de CNJ ─────────────────────────────────────────────────────

/** Remove tudo que não for dígito. Não valida o comprimento — use isValidCnj. */
export function stripCnjMask(input: string): string {
  return (input ?? '').replace(/\D/g, '');
}

/** 20 dígitos exatos — mesma regra de causaganha/processos/cnj.py:normalizar_cnj. */
export function isValidCnj(digits: string): boolean {
  return /^\d{20}$/.test(digits);
}

/** Normaliza uma entrada de usuário (com ou sem máscara) para 20 dígitos, ou '' se inválida. */
export function normalizeCnj(input: string): string {
  const digits = stripCnjMask(input);
  return isValidCnj(digits) ? digits : '';
}

/** 20 dígitos → NNNNNNN-DD.AAAA.J.TR.OOOO — mesma máscara de causaganha/processos/cnj.py:formatar_cnj. */
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
// Somente as colunas exibidas (nunca SELECT *); nr_processo/numero_processo
// filtrado via prepared statement, nunca por interpolação de string. As URLs
// interpoladas em read_parquet([...]) vêm sempre de INDICE_PROCESSUAL_URL (um
// módulo constante) ou de arquivo_ia_url descoberto no próprio índice — nunca
// de entrada do usuário.

function urlListSql(urls: string[]): string {
  return urls.map((u) => `'${u}'`).join(', ');
}

/** Descobre, para um CNJ, quais fontes têm registro e em qual parquet cada uma vive. */
export function buildIndiceSql(): string {
  return `
    SELECT fonte, arquivo_ia_url
    FROM read_parquet('${INDICE_PROCESSUAL_URL}')
    WHERE numero_processo = ?
  `;
}

export function buildDjenSql(urls: string[]): string {
  return `
    SELECT
      COUNT(*)::INTEGER AS n_publicacoes,
      MIN(data_disponibilizacao)::VARCHAR AS primeira_publicacao,
      MAX(data_disponibilizacao)::VARCHAR AS ultima_publicacao,
      list(DISTINCT tribunal) AS tribunais
    FROM read_parquet([${urlListSql(urls)}], union_by_name=true)
    WHERE regexp_replace(numero_processo, '[^0-9]', '', 'g') = ?
  `;
}

export function buildJurisSql(urls: string[]): string {
  return `
    WITH cleaned AS (
      SELECT id_documento, tipo, data_julgamento, orgao, relator, classe_judicial, url_portal
      FROM read_parquet([${urlListSql(urls)}])
      WHERE regexp_replace(nr_processo, '[^0-9]', '', 'g') = ?
    ),
    ranked AS (
      SELECT *, ROW_NUMBER() OVER (
        ORDER BY
          CASE tipo WHEN 'ACÓRDÃO' THEN 1 WHEN 'SENTENÇA' THEN 2 ELSE 9 END,
          data_julgamento DESC NULLS LAST
      ) AS rn
      FROM cleaned
    ),
    principal AS (SELECT * FROM ranked WHERE rn = 1),
    agg AS (
      SELECT
        COUNT(*)::INTEGER AS n_documentos,
        list(DISTINCT tipo) AS tipos,
        MAX(data_julgamento)::VARCHAR AS data_julgamento
      FROM cleaned
    )
    SELECT
      agg.n_documentos, agg.tipos, agg.data_julgamento,
      principal.orgao, principal.relator,
      principal.classe_judicial AS classe, principal.url_portal AS url
    FROM agg, principal
  `;
}

export function buildStjSql(urls: string[]): string {
  return `
    SELECT
      COUNT(*)::INTEGER AS n,
      FIRST(id ORDER BY "dataDecisao" DESC NULLS LAST)::VARCHAR AS id,
      FIRST("siglaClasse" ORDER BY "dataDecisao" DESC NULLS LAST) AS classe,
      FIRST("ministroRelator" ORDER BY "dataDecisao" DESC NULLS LAST) AS relator,
      FIRST("tema" ORDER BY "dataDecisao" DESC NULLS LAST)::VARCHAR AS tema,
      FIRST("teseJuridica" ORDER BY "dataDecisao" DESC NULLS LAST) AS tese,
      FIRST("ementa" ORDER BY "dataDecisao" DESC NULLS LAST) AS ementa,
      MAX("dataDecisao")::VARCHAR AS data_decisao,
      MAX("dataPublicacao")::VARCHAR AS data_publicacao
    FROM read_parquet([${urlListSql(urls)}])
    WHERE regexp_replace("numeroProcesso", '[^0-9]', '', 'g') = ?
  `;
}

export function buildDatajudSql(urls: string[]): string {
  return `
    SELECT
      COUNT(*)::INTEGER AS n,
      FIRST(classe_nome ORDER BY ultima_atualizacao DESC NULLS LAST) AS classe_oficial,
      FIRST(assuntos ORDER BY ultima_atualizacao DESC NULLS LAST) AS assuntos,
      FIRST(orgao_julgador ORDER BY ultima_atualizacao DESC NULLS LAST) AS orgao_julgador,
      FIRST(grau ORDER BY ultima_atualizacao DESC NULLS LAST) AS grau,
      MIN(data_ajuizamento)::VARCHAR AS data_ajuizamento,
      MAX(ultima_atualizacao)::VARCHAR AS ultima_atualizacao
    FROM read_parquet([${urlListSql(urls)}])
    WHERE numero_processo = ?
  `;
}

/**
 * Busca `pageSize + 1` linhas a partir de `offset` — o "+1" permite detectar
 * "há mais" sem uma segunda consulta de contagem (ver paginate()). Um branch
 * UNION ALL por fonte presente; `nParams` é quantos `?` de CNJ vêm antes do
 * `LIMIT ? OFFSET ?` final — um por branch.
 */
export function buildDocumentosSql(jurisUrls: string[], stjUrls: string[]): { sql: string; nParams: number } {
  const parts: string[] = [];
  if (jurisUrls.length > 0) {
    parts.push(`
      SELECT 'juris' AS fonte, id_documento::VARCHAR AS id_documento, tipo,
        data_julgamento::VARCHAR AS data, url_portal AS url,
        left(texto_limpo, 500) AS resumo
      FROM read_parquet([${urlListSql(jurisUrls)}])
      WHERE regexp_replace(nr_processo, '[^0-9]', '', 'g') = ?
    `);
  }
  if (stjUrls.length > 0) {
    parts.push(`
      SELECT 'stj' AS fonte, id::VARCHAR AS id_documento, "siglaClasse" AS tipo,
        "dataDecisao"::VARCHAR AS data, '' AS url, left("ementa", 500) AS resumo
      FROM read_parquet([${urlListSql(stjUrls)}])
      WHERE regexp_replace("numeroProcesso", '[^0-9]', '', 'g') = ?
    `);
  }
  const union = parts.join(' UNION ALL ');
  return { sql: `${union} ORDER BY data DESC NULLS LAST, id_documento LIMIT ? OFFSET ?`, nParams: parts.length };
}

// ── Consultas legadas (fallback de rollout, ver PROCESSOS_UNIFICADOS_URL_LEGADO) ──

export function buildProcessoUnificadoSqlLegado(): string {
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
    FROM read_parquet('${PROCESSOS_UNIFICADOS_URL_LEGADO}')
    WHERE nr_processo = ?
    LIMIT 1
  `;
}

export function buildProcessoDocumentosSqlLegado(): string {
  return `
    SELECT fonte, id_documento, tipo, data, url, resumo
    FROM read_parquet('${PROCESSO_DOCUMENTOS_URL_LEGADO}')
    WHERE nr_processo = ?
    ORDER BY data DESC NULLS LAST, id_documento
    LIMIT ? OFFSET ?
  `;
}

export interface PageResult<T> {
  items: T[];
  hasMore: boolean;
}

/** rows deve ter sido buscado com LIMIT pageSize+1 (ver buildDocumentosSql). */
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

/** TIMESTAMP arbitrário (Date, string ISO, epoch numérico) → string ISO completa, ou null. */
function toIsoTimestamp(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value.toISOString();
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'bigint') {
    const parsed = new Date(typeof value === 'bigint' ? Number(value) : value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
  }
  return null;
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

// ── Modelos de visualização por fonte ──────────────────────────────────────

export interface DjenResumoView {
  present: boolean;
  primeiraPub: string | null;
  ultimaPub: string | null;
  nPublicacoes: number | null;
  tribunais: string[];
}

export interface JurisDecisaoView {
  present: boolean;
  nDocumentos: number | null;
  tipos: string[];
  dataJulgamento: string | null;
  orgao: string | null;
  relator: string | null;
  classe: string | null;
  url: string | null;
}

export interface StjAcordaoView {
  present: boolean;
  id: string | null;
  classe: string | null;
  relator: string | null;
  tema: string | null;
  tese: string | null;
  ementa: string | null;
  dataDecisao: string | null;
  dataPublicacao: string | null;
}

export interface DatajudCapaView {
  present: boolean;
  classeOficial: string | null;
  assuntos: string | null;
  orgaoJulgador: string | null;
  grau: string | null;
  dataAjuizamento: string | null;
  ultimaAtualizacao: string | null;
}

const AUSENTE_DJEN: DjenResumoView = {
  present: false,
  primeiraPub: null,
  ultimaPub: null,
  nPublicacoes: null,
  tribunais: [],
};

const AUSENTE_JURIS: JurisDecisaoView = {
  present: false,
  nDocumentos: null,
  tipos: [],
  dataJulgamento: null,
  orgao: null,
  relator: null,
  classe: null,
  url: null,
};

const AUSENTE_STJ: StjAcordaoView = {
  present: false,
  id: null,
  classe: null,
  relator: null,
  tema: null,
  tese: null,
  ementa: null,
  dataDecisao: null,
  dataPublicacao: null,
};

const AUSENTE_DATAJUD: DatajudCapaView = {
  present: false,
  classeOficial: null,
  assuntos: null,
  orgaoJulgador: null,
  grau: null,
  dataAjuizamento: null,
  ultimaAtualizacao: null,
};

/** raw vem de buildDjenSql — sempre 1 linha (COUNT agregado), n_publicacoes=0 quando ausente. */
export function mapDjenRow(raw: Record<string, unknown> | null): DjenResumoView {
  const n = raw ? toNumber(raw.n_publicacoes) : null;
  if (!raw || !n) return AUSENTE_DJEN;
  return {
    present: true,
    primeiraPub: toIsoDate(raw.primeira_publicacao),
    ultimaPub: toIsoDate(raw.ultima_publicacao),
    nPublicacoes: n,
    tribunais: toStringArray(raw.tribunais),
  };
}

/** raw vem de buildJurisSql — 0 linhas quando ausente (cross join agg×principal vazio). */
export function mapJurisRow(raw: Record<string, unknown> | null): JurisDecisaoView {
  if (!raw) return AUSENTE_JURIS;
  return {
    present: true,
    nDocumentos: toNumber(raw.n_documentos),
    tipos: toStringArray(raw.tipos),
    dataJulgamento: toIsoDate(raw.data_julgamento),
    orgao: toNullableString(raw.orgao),
    relator: toNullableString(raw.relator),
    classe: toNullableString(raw.classe),
    url: toNullableString(raw.url),
  };
}

/** raw vem de buildStjSql — sempre 1 linha (COUNT agregado), n=0 quando ausente. */
export function mapStjRow(raw: Record<string, unknown> | null): StjAcordaoView {
  const n = raw ? toNumber(raw.n) : null;
  if (!raw || !n) return AUSENTE_STJ;
  return {
    present: true,
    id: toNullableString(raw.id),
    classe: toNullableString(raw.classe),
    relator: toNullableString(raw.relator),
    tema: toNullableString(raw.tema),
    tese: toNullableString(raw.tese),
    ementa: toNullableString(raw.ementa),
    dataDecisao: toIsoDate(raw.data_decisao),
    dataPublicacao: toIsoDate(raw.data_publicacao),
  };
}

/** raw vem de buildDatajudSql — sempre 1 linha (COUNT agregado), n=0 quando ausente. */
export function mapDatajudRow(raw: Record<string, unknown> | null): DatajudCapaView {
  const n = raw ? toNumber(raw.n) : null;
  if (!raw || !n) return AUSENTE_DATAJUD;
  return {
    present: true,
    classeOficial: toNullableString(raw.classe_oficial),
    assuntos: toNullableString(raw.assuntos),
    orgaoJulgador: toNullableString(raw.orgao_julgador),
    grau: toNullableString(raw.grau),
    dataAjuizamento: toIsoDate(raw.data_ajuizamento),
    ultimaAtualizacao: toIsoDate(raw.ultima_atualizacao),
  };
}

export interface ProcessoLegadoRow {
  nrProcesso: string;
  nrProcessoMascara: string;
  fontes: Fonte[];
  djen: DjenResumoView;
  juris: JurisDecisaoView;
  stj: StjAcordaoView;
  datajud: DatajudCapaView;
  updatedAtRaw: string | null;
}

/**
 * Converte uma linha crua de buildProcessoUnificadoSqlLegado (o schema largo
 * pré-índice) para as mesmas interfaces de visualização por fonte usadas
 * pelo caminho novo — os nomes de campo já coincidem exatamente (herdados
 * do mesmo componente antes da migração), então é uma reestruturação, não
 * uma tradução de schema.
 */
export function mapProcessoRowLegado(raw: Record<string, unknown>): ProcessoLegadoRow {
  const fontes = toStringArray(raw.fontes) as Fonte[];
  const has = (f: Fonte) => fontes.includes(f);
  const nrProcesso = String(raw.nr_processo ?? '');

  return {
    nrProcesso,
    nrProcessoMascara: toNullableString(raw.nr_processo_mascara) ?? formatCnj(nrProcesso),
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
      // acompanha o mesmo booleano, checar os dois é redundante mas
      // inofensivo caso um dia divirjam.
      present: has('datajud') && Boolean(raw.tem_datajud),
      classeOficial: toNullableString(raw.classe_oficial),
      assuntos: toNullableString(raw.assuntos),
      orgaoJulgador: toNullableString(raw.orgao_julgador),
      grau: toNullableString(raw.grau),
      dataAjuizamento: toIsoDate(raw.data_ajuizamento),
      ultimaAtualizacao: toIsoDate(raw.ultima_atualizacao),
    },
    updatedAtRaw: toIsoTimestamp(raw.updated_at),
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

/** Converte uma linha crua de buildDocumentosSql no modelo de visualização. */
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

export interface FontesPresenca {
  presentes: Fonte[];
  ausentes: Fonte[];
}

/**
 * Agrupa as 4 fontes possíveis entre as que contribuíram para este CNJ e as
 * que não têm registro no dataset. Não expõe um percentual: as 4 fontes
 * cobrem categorias diferentes de informação (ex.: nem todo processo passa
 * pelo STJ), então a ausência de uma não é "incompletude" — é a fonte não
 * tendo o que consultar.
 */
export function fontesPresenca(fontes: Fonte[]): FontesPresenca {
  const presentes = ALL_FONTES.filter((f) => fontes.includes(f));
  const ausentes = ALL_FONTES.filter((f) => !fontes.includes(f));
  return { presentes, ausentes };
}

/** Processo localizado, mas sem documentos JURIS/STJ — distinto de CNJ não encontrado. */
export function isDocumentosVazio(items: unknown[], offset: number): boolean {
  return offset === 0 && items.length === 0;
}

/** Agrupa as URLs de arquivo_ia_url do índice por fonte, sem repetição, ordenadas. */
export function fonteUrls(rows: Array<{ fonte: string; url: string }>, fonte: Fonte): string[] {
  return Array.from(new Set(rows.filter((r) => r.fonte === fonte).map((r) => r.url))).sort();
}

// ── Cobertura do dataset (indice_processual.report.json) ──────────────────

export interface FonteCobertura {
  fonte: string;
  status: string;
  registros: number;
}

export interface CoberturaResult {
  cobertura: FonteCobertura[];
  datasetGeradoEm: string | null;
}

/**
 * True quando `datasetGeradoEm` já passou de FRESHNESS_THRESHOLD_MS (48h) —
 * mesmo limiar que `evaluateSourceFreshness` usa para o site-status, reusado
 * aqui em vez de inventar um SLO paralelo (docs/SERVICE_OBJECTIVES.md).
 * Timestamp ausente/imparseável não é assumido como obsoleto: é
 * "desconhecido", já coberto pelo rótulo de exibição — ver "risco
 * silencioso" em #924.
 */
export function isDatasetStale(datasetGeradoEm: string | null, now: number): boolean {
  const ts = parseTimestamp(datasetGeradoEm);
  if (ts === null) return false;
  return now - ts > FRESHNESS_THRESHOLD_MS;
}

/** Carrega indice_processual.report.json; null quando indisponível/ilegível — nunca lança. */
export async function fetchCobertura(reportUrl: string = REPORT_URL): Promise<CoberturaResult | null> {
  try {
    const res = await fetch(reportUrl);
    if (!res.ok) return null;
    const data = await res.json();
    const sources = (data?.sources ?? {}) as Record<string, { status?: string; rows?: number }>;
    const cobertura: FonteCobertura[] = Object.entries(sources).map(([fonte, info]) => ({
      fonte,
      status: info?.status ?? 'unknown',
      registros: Number(info?.rows ?? 0),
    }));
    return { cobertura, datasetGeradoEm: typeof data?.generated_at === 'string' ? data.generated_at : null };
  } catch {
    return null;
  }
}

// ── Orquestração (DuckDB-WASM) ─────────────────────────────────────────────
// Mesma conexão AsyncDuckDB do resto do dashboard (getDuckDB()) é passada
// pelo chamador — este módulo não abre conexão nenhuma, só a usa.

interface DuckDBConnectionLike {
  prepare: (sql: string) => Promise<{
    query: (...params: unknown[]) => Promise<{ toArray: () => Array<{ toJSON: () => Record<string, unknown> }> }>;
    close: () => Promise<void>;
  }>;
}

async function queryRows(
  conn: DuckDBConnectionLike,
  sql: string,
  params: unknown[],
): Promise<Record<string, unknown>[]> {
  const stmt = await conn.prepare(sql);
  try {
    const result = await stmt.query(...params);
    return result.toArray().map((row) => row.toJSON());
  } finally {
    await stmt.close();
  }
}

/**
 * Como queryRows, mas isolada por fonte: uma falha (404, CORS, parquet
 * corrompido, erro transitório) vira aviso identificando `fonte` e resolve
 * para null em vez de propagar — a mesma fronteira que
 * causaganha.processos.service.py's `_build_djen`/`_build_juris`/etc. já
 * aplicam no lado Python (RFC 0014 M2 review: sem isso, uma única fonte
 * fora do ar derrubava o dossiê inteiro para 'source_unavailable' no
 * componente, descartando as demais fontes que carregaram normalmente).
 */
async function queryRowSafe(
  conn: DuckDBConnectionLike,
  fonte: Fonte,
  sql: string,
  params: unknown[],
  avisos: string[],
): Promise<Record<string, unknown> | null> {
  try {
    const rows = await queryRows(conn, sql, params);
    return rows[0] ?? null;
  } catch (err) {
    const detalhe = err instanceof Error ? err.message : String(err);
    avisos.push(`Fonte '${fonte}' indisponível para este processo: ${detalhe}`);
    return null;
  }
}

export interface ProcessoResultado {
  encontrado: boolean;
  nrProcesso: string;
  nrProcessoMascara: string;
  fontes: Fonte[];
  djen: DjenResumoView;
  juris: JurisDecisaoView;
  stj: StjAcordaoView;
  datajud: DatajudCapaView;
  /** URLs de origem descobertas no índice — reusadas por carregarDocumentos() sem nova consulta ao índice. */
  jurisUrls: string[];
  stjUrls: string[];
  cobertura: FonteCobertura[];
  datasetGeradoEm: string | null;
  avisos: string[];
  /** True quando este resultado veio do fallback pré-migração (ver PROCESSOS_UNIFICADOS_URL_LEGADO). */
  legado: boolean;
}

const INDICE_INDISPONIVEL_AVISO =
  'Não foi possível abrir indice_processual.parquet no Internet Archive. Mostrando dados de ' +
  'processos_unificados.parquet (versão anterior à migração para o índice fino) — podem estar ' +
  'desatualizados.';

/**
 * Busca o dossiê unificado de um CNJ (20 dígitos) via indice_processual.parquet
 * + parquets de origem. Espelha causaganha/processos/service.py:buscar_processo
 * — não conhece FastMCP/Svelte, só DuckDB. Uma fonte de origem específica ou o
 * relatório de cobertura falhando vira lacuna vazia + aviso, nunca lança.
 *
 * indice_processual.parquet em si sendo inacessível (não apenas uma fonte
 * específica) não propaga como erro aqui — ao contrário do serviço Python,
 * que não tem alternativa e por isso deixa a exceção subir — porque há um
 * fallback real disponível no navegador: processos_unificados.parquet
 * (RFC 0014 M2 review). Ver buscarProcessoLegado.
 */
export async function buscarProcesso(conn: DuckDBConnectionLike, digits: string): Promise<ProcessoResultado> {
  const avisos: string[] = [];
  const coberturaResult = await fetchCobertura();
  const cobertura = coberturaResult?.cobertura ?? [];
  const datasetGeradoEm = coberturaResult?.datasetGeradoEm ?? null;
  if (!coberturaResult) avisos.push(RELATORIO_INDISPONIVEL_AVISO);

  const nrProcessoMascara = formatCnj(digits);
  let indiceRows: Record<string, unknown>[];
  try {
    indiceRows = await queryRows(conn, buildIndiceSql(), [digits]);
  } catch {
    return buscarProcessoLegado(conn, digits, nrProcessoMascara, avisos);
  }

  if (indiceRows.length === 0) {
    return {
      encontrado: false,
      nrProcesso: digits,
      nrProcessoMascara,
      fontes: [],
      djen: AUSENTE_DJEN,
      juris: AUSENTE_JURIS,
      stj: AUSENTE_STJ,
      datajud: AUSENTE_DATAJUD,
      jurisUrls: [],
      stjUrls: [],
      cobertura,
      datasetGeradoEm,
      avisos,
      legado: false,
    };
  }

  const rowPairs = indiceRows.map((r) => ({ fonte: String(r.fonte), url: String(r.arquivo_ia_url) }));
  const fontes = (Array.from(new Set(rowPairs.map((r) => r.fonte))).sort() as Fonte[]).filter((f) =>
    ALL_FONTES.includes(f),
  );
  const djenUrls = fonteUrls(rowPairs, 'djen');
  const jurisUrls = fonteUrls(rowPairs, 'juris');
  const stjUrls = fonteUrls(rowPairs, 'stj');
  const datajudUrls = fonteUrls(rowPairs, 'datajud');

  const djenRaw = djenUrls.length ? await queryRowSafe(conn, 'djen', buildDjenSql(djenUrls), [digits], avisos) : null;
  const jurisRaw = jurisUrls.length
    ? await queryRowSafe(conn, 'juris', buildJurisSql(jurisUrls), [digits], avisos)
    : null;
  const stjRaw = stjUrls.length ? await queryRowSafe(conn, 'stj', buildStjSql(stjUrls), [digits], avisos) : null;
  const datajudRaw = datajudUrls.length
    ? await queryRowSafe(conn, 'datajud', buildDatajudSql(datajudUrls), [digits], avisos)
    : null;

  return {
    encontrado: true,
    nrProcesso: digits,
    nrProcessoMascara,
    fontes,
    djen: mapDjenRow(djenRaw),
    juris: mapJurisRow(jurisRaw),
    stj: mapStjRow(stjRaw),
    datajud: mapDatajudRow(datajudRaw),
    jurisUrls,
    stjUrls,
    cobertura,
    datasetGeradoEm,
    avisos,
    legado: false,
  };
}

/**
 * Fallback de rollout: indice_processual.parquet está inacessível — tenta o
 * schema largo pré-migração (ainda no IA, congelado). Se ele também falhar,
 * não há fonte de dados nenhuma disponível — deixa a exceção subir para o
 * chamador tratar como "fonte indisponível" (mesmo comportamento de antes
 * desta fallback existir).
 */
async function buscarProcessoLegado(
  conn: DuckDBConnectionLike,
  digits: string,
  nrProcessoMascara: string,
  avisosBase: string[],
): Promise<ProcessoResultado> {
  const avisos = [...avisosBase, INDICE_INDISPONIVEL_AVISO];
  const rows = await queryRows(conn, buildProcessoUnificadoSqlLegado(), [digits]);

  if (rows.length === 0) {
    return {
      encontrado: false,
      nrProcesso: digits,
      nrProcessoMascara,
      fontes: [],
      djen: AUSENTE_DJEN,
      juris: AUSENTE_JURIS,
      stj: AUSENTE_STJ,
      datajud: AUSENTE_DATAJUD,
      jurisUrls: [],
      stjUrls: [],
      cobertura: [],
      datasetGeradoEm: null,
      avisos,
      legado: true,
    };
  }

  const legado = mapProcessoRowLegado(rows[0]);
  return {
    encontrado: true,
    nrProcesso: legado.nrProcesso,
    nrProcessoMascara: legado.nrProcessoMascara,
    fontes: legado.fontes,
    djen: legado.djen,
    juris: legado.juris,
    stj: legado.stj,
    datajud: legado.datajud,
    jurisUrls: [],
    stjUrls: [],
    cobertura: [],
    datasetGeradoEm: legado.updatedAtRaw,
    avisos,
    legado: true,
  };
}

/**
 * Busca uma página de documentos JURIS/STJ para um CNJ já resolvido por
 * buscarProcesso() — reusa `jurisUrls`/`stjUrls` descobertas ali, sem
 * reconsultar o índice. Retorna vazio sem consultar nada quando nenhuma das
 * duas fontes tem registro (também o caso quando `legado=true`, já que o
 * fallback não descobre URLs de origem — carregarDocumentos precisa do
 * parâmetro `legado` nesse caso para consultar processo_documentos.parquet
 * em vez do UNION dinâmico por fonte).
 */
export async function carregarDocumentos(
  conn: DuckDBConnectionLike,
  jurisUrls: string[],
  stjUrls: string[],
  digits: string,
  offset: number,
  pageSize: number = DOCUMENTOS_PAGE_SIZE,
  legado = false,
): Promise<PageResult<ProcessoDocumentoRow>> {
  if (legado) {
    const rawRows = await queryRows(conn, buildProcessoDocumentosSqlLegado(), [
      digits,
      pageSize + 1,
      offset,
    ]);
    return paginate(rawRows.map(mapDocumentoRow), pageSize);
  }
  if (jurisUrls.length === 0 && stjUrls.length === 0) {
    return { items: [], hasMore: false };
  }
  const { sql, nParams } = buildDocumentosSql(jurisUrls, stjUrls);
  const params = [...Array(nParams).fill(digits), pageSize + 1, offset];
  const rawRows = await queryRows(conn, sql, params);
  return paginate(rawRows.map(mapDocumentoRow), pageSize);
}
