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
import { serializeSharedCore, type SharedCore } from './processoContract';

export const IA_DASHBOARD_BASE = 'https://archive.org/download/causaganha-dashboard';
export const INDICE_PROCESSUAL_URL = `${IA_DASHBOARD_BASE}/indice_processual.parquet`;
export const REPORT_URL = `${IA_DASHBOARD_BASE}/indice_processual.report.json`;

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

export type HeroSearchMode = 'processo' | 'publicacoes';

export interface HeroSearchHint {
  mode: HeroSearchMode | null;
  label: string;
}

/**
 * Mensagem exibida sob a busca da home enquanto o usuário digita (#1127) —
 * mesma autoridade de parsing de buildHeroSearchRedirect (classifyCnjInput),
 * para não criar uma terceira semântica de CNJ vs texto livre.
 */
export function describeHeroSearchMode(raw: string): HeroSearchHint {
  const status = classifyCnjInput(raw);
  if (status === 'empty') return { mode: null, label: '' };
  if (status === 'valid') return { mode: 'processo', label: 'Abrir dossiê do processo' };
  return { mode: 'publicacoes', label: 'Pesquisar publicações' };
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

/**
 * Descobre, para um CNJ, quais fontes têm registro e em qual parquet cada uma vive.
 *
 * `url` aceita um override explícito — mirando `causaganha.processos.service._indice_sql(url)`
 * — para que o harness de paridade de plano de consulta (#1107) possa exercitar este
 * builder contra a mesma fixture local que os demais já usam, em vez de ficar
 * permanentemente amarrado à URL de produção.
 *
 * `tribunal` é selecionado para a checagem de coerência de proveniência
 * (issue #1610, TM-04) feita por `fonteUrls`/`validarTribunalCoerente` --
 * espelha `_indice_sql` do lado Python.
 */
export function buildIndiceSql(url: string = INDICE_PROCESSUAL_URL): string {
  return `
    SELECT fonte, arquivo_ia_url, tribunal
    FROM read_parquet('${url}')
    WHERE numero_processo = ?
  `;
}

/**
 * "direct" is only safe when every DJEN file in the search certifies the
 * CNJ-text-sorted layout (see `resolveDjenEqualityMode`) — otherwise a
 * masked/legacy `numero_processo` value would silently fail to match.
 */
export type DjenEqualityMode = 'direct' | 'compatible';

export function buildDjenSql(urls: string[], equalityMode: DjenEqualityMode = 'compatible'): string {
  const whereClause =
    equalityMode === 'direct' ? 'numero_processo = ?' : "regexp_replace(numero_processo, '[^0-9]', '', 'g') = ?";
  return `
    SELECT
      COUNT(*)::INTEGER AS n_publicacoes,
      MIN(data_disponibilizacao)::VARCHAR AS primeira_publicacao,
      MAX(data_disponibilizacao)::VARCHAR AS ultima_publicacao,
      list(DISTINCT tribunal) AS tribunais
    FROM read_parquet([${urlListSql(urls)}], union_by_name=true)
    WHERE ${whereClause}
  `;
}

// ── Certificação do rodapé (#1469) ─────────────────────────────────────────
// `exporter.py` normaliza numero_processo para texto de 20 dígitos e ordena
// CNJ-first apenas nas tabelas em CNJ_LAYOUT_TABLES, certificando isso no
// rodapé Parquet (causaganha.layout, causaganha.cnj_normalization). Só então
// a leitura pode trocar o `regexp_replace` (por linha, nunca podado por
// estatísticas de row-group) por igualdade direta — o motivo inteiro de
// reordenar por CNJ na escrita.

const LAYOUT_MARKER_KEY = 'causaganha.layout';
const LAYOUT_MARKER_VALUE = 'cnj-text-sorted-v1';
const CNJ_NORMALIZATION_MARKER_KEY = 'causaganha.cnj_normalization';
const CNJ_NORMALIZATION_MARKER_VALUE = 'valid-20-digits-v1';

export interface DjenKvMetadataRow {
  file_name: string;
  key: string;
  value: string;
}

/** Lê os pares chave/valor do rodapé Parquet de cada arquivo DJEN descoberto. */
export function buildDjenCertificationSql(urls: string[]): string {
  return `
    SELECT file_name, key, value
    FROM parquet_kv_metadata([${urlListSql(urls)}])
  `;
}

/**
 * Igualdade direta só é segura quando TODOS os arquivos da busca certificam
 * os dois marcadores com o valor exato -- um arquivo sem marcador nenhum
 * (legado), com só um dos dois, ou com um valor diferente do esperado
 * (versão futura do layout) volta para o caminho compatível, exatamente como
 * uma busca que mistura um arquivo certificado com um legado (#1469).
 */
export function resolveDjenEqualityMode(urls: string[], kvRows: DjenKvMetadataRow[]): DjenEqualityMode {
  if (urls.length === 0) return 'compatible';
  const markersByFile = new Map<string, Map<string, string>>();
  for (const row of kvRows) {
    if (!markersByFile.has(row.file_name)) markersByFile.set(row.file_name, new Map());
    markersByFile.get(row.file_name)!.set(row.key, row.value);
  }
  const allCertified = urls.every((url) => {
    const markers = markersByFile.get(url);
    return (
      markers?.get(LAYOUT_MARKER_KEY) === LAYOUT_MARKER_VALUE &&
      markers?.get(CNJ_NORMALIZATION_MARKER_KEY) === CNJ_NORMALIZATION_MARKER_VALUE
    );
  });
  return allCertified ? 'direct' : 'compatible';
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
      MAX("dataDecisao")::DATE AS data_decisao,
      MAX("dataPublicacao")::DATE AS data_publicacao
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
        "dataDecisao"::DATE AS data, '' AS url, left("ementa", 500) AS resumo
      FROM read_parquet([${urlListSql(stjUrls)}])
      WHERE regexp_replace("numeroProcesso", '[^0-9]', '', 'g') = ?
    `);
  }
  const union = parts.join(' UNION ALL ');
  return { sql: `${union} ORDER BY data DESC NULLS LAST, id_documento LIMIT ? OFFSET ?`, nParams: parts.length };
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

const BARE_ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?)?$/;

/**
 * Valida que (ano, mês, dia) formam uma data de calendário real, sem
 * depender de `new Date()` reinterpretar hora local: passar componentes
 * fora de faixa (mês 13, dia 32, 29/02 em ano não-bissexto) rola para o
 * mês/ano seguinte, então o round-trip só bate se a entrada já era válida.
 * Usa `setUTCFullYear(year, ...)` em vez de `Date.UTC(year, ...)`/
 * `new Date(year, ...)` -- essas duas últimas aplicam a regra legada que
 * mapeia um ano de 0-99 para 1900-1999, o que rejeitaria incorretamente um
 * ano ISO válido abaixo de 100 (que `new Date(isoString)` sempre aceitou).
 */
function isValidCalendarDate(year: number, month: number, day: number): boolean {
  const asUtc = new Date(0);
  asUtc.setUTCFullYear(year, month - 1, day);
  return (
    asUtc.getUTCFullYear() === year && asUtc.getUTCMonth() === month - 1 && asUtc.getUTCDate() === day
  );
}

/**
 * DATE/TIMESTAMP arbitrário (Date, string ISO, epoch numérico) → 'YYYY-MM-DD', ou null.
 *
 * Uma string 'YYYY-MM-DD[ T]HH:MM:SS' sem sufixo 'Z'/offset (ex.:
 * datajud.models.normalizar_data14) é ingênua, não um instante absoluto: o
 * componente de data é extraído diretamente, sem reinterpretar via `new
 * Date()` -- que a tratamos como hora local e corromperia o dia em qualquer
 * fuso UTC+ (mesmo raciocínio do docstring de `toIsoTimestamp`). Rejeita
 * (retorna null) quando os dígitos extraídos não formam uma data de
 * calendário real -- normalizar_data14 só extrai grupos de dígitos e pode
 * emitir mês/dia (ou hora/minuto/segundo, quando presentes) fora de faixa
 * sem validar.
 */
export function toIsoDate(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') {
    const bareMatch = BARE_ISO_DATE_RE.exec(value);
    if (bareMatch) {
      const [, y, m, d, hh, mm, ss] = bareMatch;
      if (!isValidCalendarDate(Number(y), Number(m), Number(d))) return null;
      if (hh !== undefined && (Number(hh) > 23 || Number(mm) > 59 || Number(ss) > 59)) return null;
      return `${y}-${m}-${d}`;
    }
  }
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value.toISOString().slice(0, 10);
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'bigint') {
    const parsed = new Date(typeof value === 'bigint' ? Number(value) : value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString().slice(0, 10);
  }
  return null;
}

/**
 * DuckDB VARCHAR-cast TIMESTAMP/DATE arbitrário → string ISO 8601 preservando
 * hora quando presente, ou null.
 *
 * Ao contrário de `toIsoDate`, não trunca o componente de hora e não
 * reinterpreta a string via `Date` (o que corromperia o instante para
 * timestamps ingênuos em fusos não-UTC) — apenas normaliza o separador
 * espaço→'T' que o cast `::VARCHAR` do DuckDB produz para TIMESTAMP, para
 * igualar `datetime.isoformat()` do lado Python (service.py:_iso). Uma
 * string já 'YYYY-MM-DD' (coluna DATE) permanece inalterada, igual ao
 * `date.isoformat()` do Python para a mesma coluna.
 */
export function toIsoTimestamp(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  const s = String(value);
  if (s.length === 0) return null;
  const match = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}.*)$/.exec(s);
  return match ? `${match[1]}T${match[2]}` : s;
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
    ultimaAtualizacao: toIsoTimestamp(raw.ultima_atualizacao),
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

/** Papel de produto de cada fonte (docs/PRODUCT.md): Arquivo, Estado ou Teor. */
export type Papel = 'arquivo' | 'estado' | 'teor';

export const FONTE_PAPEL: Record<Fonte, Papel> = {
  djen: 'arquivo',
  datajud: 'estado',
  juris: 'teor',
  stj: 'teor',
};

export type EvidenceStatus = 'presente' | 'ausente' | 'indisponivel';

export interface EvidenceMatrixRow {
  fonte: Fonte;
  papel: Papel;
  status: EvidenceStatus;
}

/**
 * Uma linha por fonte para a faixa-resumo de evidências de #1130. Não faz
 * nenhuma consulta nova: só relê `fontes` (presença por CNJ), `avisos`
 * (falha de consulta a uma fonte específica, texto livre já produzido por
 * `queryRowSafe`) e `cobertura` (status do dataset por fonte, já produzido
 * por `fetchCobertura`). Indisponibilidade tem precedência sobre ausência —
 * uma fonte que falhou a consulta está, por construção, também ausente de
 * `fontes` (ver queryRowSafe), e as duas situações precisam continuar
 * visualmente distintas (#1130).
 */
export function evidenceMatrixRows(
  fontes: Fonte[],
  avisos: string[],
  cobertura: FonteCobertura[],
): EvidenceMatrixRow[] {
  return ALL_FONTES.map((fonte) => {
    const avisoIndisponivel = avisos.some((aviso) => aviso.startsWith(`Fonte '${fonte}' indisponível`));
    const coberturaIndisponivel = cobertura.some((c) => c.fonte === fonte && c.status === 'unavailable');
    const status: EvidenceStatus =
      avisoIndisponivel || coberturaIndisponivel
        ? 'indisponivel'
        : fontes.includes(fonte)
          ? 'presente'
          : 'ausente';
    return { fonte, papel: FONTE_PAPEL[fonte], status };
  });
}

/** Processo localizado, mas sem documentos JURIS/STJ — distinto de CNJ não encontrado. */
export function isDocumentosVazio(items: unknown[], offset: number): boolean {
  return offset === 0 && items.length === 0;
}

// Issue #1610: arquivo_ia_url values come from indice_processual.parquet
// itself -- a canonical manifest artifact, not user input, but one a
// compromised upstream could poison. They are interpolated as-is into
// read_parquet([...])/parquet_kv_metadata([...]) by urlListSql, so an
// unvalidated value could redirect DuckDB's fetch target or break out of
// that string literal. Mirrors causaganha.processos.service
// ._validate_artifact_url (#1622) -- same policy, same allowlist.
const ARTIFACT_ALLOWED_HOST = 'archive.org';
const ARTIFACT_ALLOWED_PATH_PREFIX = '/download/';
const ARTIFACT_ALLOWED_PATH_SUFFIX = '.parquet';

/** A manifest-provided artifact URL failed the fetch policy (issue #1610). */
export class ArtifactUrlError extends Error {}

/**
 * Fails closed on anything that isn't a same-host, same-path-shape IA
 * parquet URL -- or a bare, scheme-less local path (kept so test fixtures,
 * which stand in for remote IA URLs, keep working unchanged).
 */
export function validateArtifactUrl(url: string): string {
  if (url.includes("'")) {
    throw new ArtifactUrlError(`URL de artefato contém aspas simples: ${JSON.stringify(url)}`);
  }
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return url;
  }
  if (parsed.protocol !== 'https:' || parsed.hostname.toLowerCase() !== ARTIFACT_ALLOWED_HOST) {
    throw new ArtifactUrlError(`Host/esquema de artefato não permitido: ${JSON.stringify(url)}`);
  }
  if (parsed.search || parsed.hash) {
    throw new ArtifactUrlError(`URL de artefato não pode ter query/fragment: ${JSON.stringify(url)}`);
  }
  if (!parsed.pathname.startsWith(ARTIFACT_ALLOWED_PATH_PREFIX) || !parsed.pathname.endsWith(ARTIFACT_ALLOWED_PATH_SUFFIX)) {
    throw new ArtifactUrlError(`Path de artefato fora do padrão esperado: ${JSON.stringify(url)}`);
  }
  return url;
}

// Issue #1610 (TM-04): `indice_processual.parquet` also carries a `tribunal`
// column per row -- an independent claim about the same fact `arquivo_ia_url`
// encodes for the two sources partitioned per tribunal (djen's IA item is
// `djen-{tribunal}-{ano}`; datajud's is `datajud-{tribunal}`, per CLAUDE.md's
// "IA item naming"). A manifest row that passes the URL policy above but
// disagrees with itself about which tribunal it describes is still a
// "controle de significado" threat (attribution/omission without needing a
// bad fetch destination) -- juris/stj are single, fixed items regardless of
// tribunal, so there is nothing to cross-check there. Mirrors
// causaganha.processos.service._tribunal_da_url/_validar_tribunal_coerente.
const TRIBUNAL_URL_PATTERNS: Partial<Record<Fonte, RegExp>> = {
  djen: /\/download\/djen-([a-z0-9]+)-\d{4}\//,
  datajud: /\/download\/datajud-([a-z0-9]+)\//,
};

/** A manifest row's `tribunal` disagrees with the tribunal its own `arquivo_ia_url` names (issue #1610). */
export class ArtifactProvenanceError extends Error {}

/**
 * Tribunal (lowercase) embutido no nome do item IA de `url`, para uma fonte
 * particionada por tribunal. `null` quando `fonte` não é particionada por
 * tribunal, ou quando `url` não tem o formato esperado de item IA (ex.: um
 * path local de teste) -- em ambos os casos não há reivindicação
 * independente contra a qual checar a coluna `tribunal` do índice.
 */
export function tribunalDaUrl(fonte: Fonte, url: string): string | null {
  const pattern = TRIBUNAL_URL_PATTERNS[fonte];
  if (!pattern) return null;
  const match = pattern.exec(url);
  return match ? match[1] : null;
}

/** Lança `ArtifactProvenanceError` quando `url` nomeia um tribunal diferente do que a coluna `tribunal` do índice declara para esta linha. */
export function validarTribunalCoerente(fonte: Fonte, tribunal: string, url: string): void {
  const esperado = tribunalDaUrl(fonte, url);
  if (esperado !== null && esperado !== tribunal.toLowerCase()) {
    throw new ArtifactProvenanceError(
      `Tribunal declarado no índice (${JSON.stringify(tribunal)}) incoerente com o tribunal ` +
        `do artefato (${JSON.stringify(esperado)}) para fonte ${JSON.stringify(fonte)}: ${JSON.stringify(url)}`,
    );
  }
}

// Issue #1610 (TM-04), fatia "schema fingerprint"/"generation id": todo
// export djen (comunicacoes/processos) já grava KV_METADATA no rodapé do
// próprio arquivo Parquet -- causaganha.schema_version e causaganha.item_id
// (schema_registry.kv_metadata_for_export, ativo desde a v3.0.0) -- mas nada
// do lado Web lia esse rodapé antes de compor read_parquet(arquivo_ia_url).
// Diferente de validarTribunalCoerente (que só cruza duas strings do próprio
// índice), esta checagem lê o que o artefato de origem *declara sobre si
// mesmo*, via parquet_kv_metadata() -- uma leitura do rodapé Parquet (barata,
// via httpfs range-read; não baixa o arquivo inteiro). juris e datajud
// também já emitem e validam esse rodapé (ver validarMetadataJuris/
// validarMetadataDatajud abaixo); stj continua sem cobertura porque
// stj_acordaos não tem nenhum pipeline write_parquet/to_parquet sob
// controle deste repo hoje. Mirrors
// causaganha.processos.service._item_id_da_url/_validar_metadata_djen.
const DJEN_ITEM_ID_PATTERN = /\/download\/(djen-[a-z0-9]+-\d{4})\//;

// Mirrors SCHEMA_REGISTRY's keys (src/causaganha/consolidate/schema_registry.py)
// -- duplicated here, not imported, because the Python registry isn't
// available to a browser build. Same accepted-duplication risk already
// documented for the artifact URL policy (Python _validate_artifact_url vs
// TS validateArtifactUrl, #1610 next_move): a new schema version must be
// added here too, or a coherent djen artifact would fail this check.
const KNOWN_DJEN_SCHEMA_VERSIONS = new Set(['3.0.0']);

/** IA item id (`djen-{tribunal}-{ano}`) embutido no path de `url`, ou `null` quando `url` não tem o formato de artefato djen (ex.: path local de teste). */
export function itemIdDaUrl(url: string): string | null {
  const match = DJEN_ITEM_ID_PATTERN.exec(url);
  return match ? match[1] : null;
}

/**
 * Lança `ArtifactProvenanceError` quando o rodapé Parquet (`metadata`) de um
 * artefato djen discorda de (ou não carrega) a identidade que sua
 * `arquivo_ia_url` reivindica -- um artefato comprometido/trocado sob uma URL
 * inalterada, não só uma string ruim na linha do manifesto.
 */
export function validarMetadataDjen(url: string, metadata: Record<string, string>): void {
  const esperadoItemId = itemIdDaUrl(url);
  if (esperadoItemId === null) return;
  const schemaVersion = metadata['causaganha.schema_version'];
  if (schemaVersion === undefined || !KNOWN_DJEN_SCHEMA_VERSIONS.has(schemaVersion)) {
    throw new ArtifactProvenanceError(
      `Artefato djen sem schema_version reconhecido no rodapé Parquet ` +
        `(${JSON.stringify(schemaVersion ?? null)}): ${JSON.stringify(url)}`,
    );
  }
  const itemId = metadata['causaganha.item_id'];
  if (itemId !== esperadoItemId) {
    throw new ArtifactProvenanceError(
      `Artefato djen declara item_id ${JSON.stringify(itemId ?? null)} no rodapé Parquet, mas ` +
        `a URL do índice aponta para ${JSON.stringify(esperadoItemId)}: ${JSON.stringify(url)}`,
    );
  }
}

/** SQL do rodapé Parquet de um único artefato djen -- leitura de footer (httpfs range-read), não do arquivo inteiro. */
export function buildDjenArtifactMetadataSql(url: string): string {
  return `SELECT key, value FROM parquet_kv_metadata('${url}')`;
}

/**
 * `djenUrls` cujo rodapé Parquet passa `validarMetadataDjen`, descartando
 * (com aviso em `avisos`, nunca uma exceção fatal) qualquer um que falhe a
 * leitura ou a checagem -- mesma política non-fatal-per-artifact do resto
 * deste módulo. Cada URL é consultada individualmente (não em lote) para que
 * a falha de leitura de um artefato não degrade os demais. Diferente do lado
 * Python (que sempre lê o rodapé antes de checar a forma da URL), aqui a
 * leitura só é tentada quando `itemIdDaUrl` já reconhece a URL como um item
 * djen -- uma URL sem essa forma (ex.: fixture local de teste) não tem
 * reivindicação para verificar, então não vale a pena arriscar uma consulta
 * de rede/uma falha de leitura só para descartá-la sem necessidade.
 */
export async function validarMetadataDjenUrls(
  conn: DuckDBConnectionLike,
  djenUrls: string[],
  avisos: string[],
): Promise<string[]> {
  const validated: string[] = [];
  for (const url of djenUrls) {
    if (itemIdDaUrl(url) === null) {
      validated.push(url);
      continue;
    }
    try {
      const rows = await queryRows(conn, buildDjenArtifactMetadataSql(url), []);
      const metadata: Record<string, string> = {};
      for (const row of rows) metadata[String(row.key)] = String(row.value);
      validarMetadataDjen(url, metadata);
    } catch (err) {
      if (err instanceof ArtifactProvenanceError) {
        avisos.push(`Fonte 'djen' descartou um artefato com ${err.message}`);
      } else {
        const detalhe = err instanceof Error ? err.message : String(err);
        avisos.push(`Fonte 'djen' descartou um artefato sem rodapé Parquet legível: ${detalhe}`);
      }
      continue;
    }
    validated.push(url);
  }
  return validated;
}

// TM-04 read side for `juris` (issue #1610): o lado de escrita
// (`tjro_juris.service._rows_to_parquet`) agora grava o mesmo rodapé
// `causaganha.schema_version`/`causaganha.item_id` que os exports djen já
// gravam, no mesmo namespace `causaganha.*` (`JURIS_SCHEMA_VERSION` em vez de
// `SCHEMA_REGISTRY`, já que juris tem um único schema de export até agora,
// sem versionamento). Mirrors causaganha.processos.service
// ._juris_item_id_da_url/_validar_metadata_juris (Python) -- mesma política,
// mesma checagem, superfície TS.
const JURIS_ITEM_ID_PATTERN = /\/download\/(tjro-juris-\d{4})\//;

// Mirrors JURIS_SCHEMA_VERSION (src/tjro_juris/service.py) -- duplicado
// aqui pelo mesmo motivo aceito para KNOWN_DJEN_SCHEMA_VERSIONS: o registro
// Python não está disponível para um build de browser.
const KNOWN_JURIS_SCHEMA_VERSIONS = new Set(['1.0.0']);

/** IA item id (`tjro-juris-{ano}`) embutido no path de `url`, ou `null` quando `url` não tem o formato de artefato juris (ex.: path local de teste). */
export function jurisItemIdDaUrl(url: string): string | null {
  const match = JURIS_ITEM_ID_PATTERN.exec(url);
  return match ? match[1] : null;
}

/**
 * Lança `ArtifactProvenanceError` quando o rodapé Parquet (`metadata`) de um
 * artefato juris discorda de (ou não carrega) a identidade que sua
 * `arquivo_ia_url` reivindica -- espelho de `validarMetadataDjen` para juris.
 */
export function validarMetadataJuris(url: string, metadata: Record<string, string>): void {
  const esperadoItemId = jurisItemIdDaUrl(url);
  if (esperadoItemId === null) return;
  const schemaVersion = metadata['causaganha.schema_version'];
  if (schemaVersion === undefined || !KNOWN_JURIS_SCHEMA_VERSIONS.has(schemaVersion)) {
    throw new ArtifactProvenanceError(
      `Artefato juris sem schema_version reconhecido no rodapé Parquet ` +
        `(${JSON.stringify(schemaVersion ?? null)}): ${JSON.stringify(url)}`,
    );
  }
  const itemId = metadata['causaganha.item_id'];
  if (itemId !== esperadoItemId) {
    throw new ArtifactProvenanceError(
      `Artefato juris declara item_id ${JSON.stringify(itemId ?? null)} no rodapé Parquet, mas ` +
        `a URL do índice aponta para ${JSON.stringify(esperadoItemId)}: ${JSON.stringify(url)}`,
    );
  }
}

/** SQL do rodapé Parquet de um único artefato juris -- leitura de footer (httpfs range-read), não do arquivo inteiro. */
export function buildJurisArtifactMetadataSql(url: string): string {
  return `SELECT key, value FROM parquet_kv_metadata('${url}')`;
}

/**
 * `jurisUrls` cujo rodapé Parquet passa `validarMetadataJuris`, descartando
 * (com aviso em `avisos`, nunca uma exceção fatal) qualquer um que falhe a
 * leitura ou a checagem -- mesma política non-fatal-per-artifact de
 * `validarMetadataDjenUrls`.
 */
export async function validarMetadataJurisUrls(
  conn: DuckDBConnectionLike,
  jurisUrls: string[],
  avisos: string[],
): Promise<string[]> {
  const validated: string[] = [];
  for (const url of jurisUrls) {
    if (jurisItemIdDaUrl(url) === null) {
      validated.push(url);
      continue;
    }
    try {
      const rows = await queryRows(conn, buildJurisArtifactMetadataSql(url), []);
      const metadata: Record<string, string> = {};
      for (const row of rows) metadata[String(row.key)] = String(row.value);
      validarMetadataJuris(url, metadata);
    } catch (err) {
      if (err instanceof ArtifactProvenanceError) {
        avisos.push(`Fonte 'juris' descartou um artefato com ${err.message}`);
      } else {
        const detalhe = err instanceof Error ? err.message : String(err);
        avisos.push(`Fonte 'juris' descartou um artefato sem rodapé Parquet legível: ${detalhe}`);
      }
      continue;
    }
    validated.push(url);
  }
  return validated;
}

// TM-04 read side for `datajud` (issue #1610): o lado de escrita
// (`datajud.archive._write_parquet`) agora grava o mesmo rodapé
// `causaganha.schema_version`/`causaganha.item_id` que os exports djen e
// juris já gravam, no mesmo namespace `causaganha.*`
// (`DATAJUD_SCHEMA_VERSION` em vez de `SCHEMA_REGISTRY`, já que datajud tem
// um único schema de export até agora, sem versionamento). Mirrors
// causaganha.processos.service
// ._datajud_item_id_da_url/_validar_metadata_datajud (Python) -- mesma
// política, mesma checagem, superfície TS, contra a forma de item
// `datajud-{tribunal}` (sem sufixo de ano) em vez de `tjro-juris-{ano}`.
const DATAJUD_ITEM_ID_PATTERN = /\/download\/(datajud-[a-z0-9]+)\//;

// Mirrors DATAJUD_SCHEMA_VERSION (src/datajud/archive.py) -- duplicado aqui
// pelo mesmo motivo aceito para KNOWN_DJEN_SCHEMA_VERSIONS/
// KNOWN_JURIS_SCHEMA_VERSIONS: o registro Python não está disponível para
// um build de browser.
const KNOWN_DATAJUD_SCHEMA_VERSIONS = new Set(['1.0.0']);

/** IA item id (`datajud-{tribunal}`) embutido no path de `url`, ou `null` quando `url` não tem o formato de artefato datajud (ex.: path local de teste). */
export function datajudItemIdDaUrl(url: string): string | null {
  const match = DATAJUD_ITEM_ID_PATTERN.exec(url);
  return match ? match[1] : null;
}

/**
 * Lança `ArtifactProvenanceError` quando o rodapé Parquet (`metadata`) de um
 * artefato datajud discorda de (ou não carrega) a identidade que sua
 * `arquivo_ia_url` reivindica -- espelho de `validarMetadataDjen` para datajud.
 */
export function validarMetadataDatajud(url: string, metadata: Record<string, string>): void {
  const esperadoItemId = datajudItemIdDaUrl(url);
  if (esperadoItemId === null) return;
  const schemaVersion = metadata['causaganha.schema_version'];
  if (schemaVersion === undefined || !KNOWN_DATAJUD_SCHEMA_VERSIONS.has(schemaVersion)) {
    throw new ArtifactProvenanceError(
      `Artefato datajud sem schema_version reconhecido no rodapé Parquet ` +
        `(${JSON.stringify(schemaVersion ?? null)}): ${JSON.stringify(url)}`,
    );
  }
  const itemId = metadata['causaganha.item_id'];
  if (itemId !== esperadoItemId) {
    throw new ArtifactProvenanceError(
      `Artefato datajud declara item_id ${JSON.stringify(itemId ?? null)} no rodapé Parquet, mas ` +
        `a URL do índice aponta para ${JSON.stringify(esperadoItemId)}: ${JSON.stringify(url)}`,
    );
  }
}

/** SQL do rodapé Parquet de um único artefato datajud -- leitura de footer (httpfs range-read), não do arquivo inteiro. */
export function buildDatajudArtifactMetadataSql(url: string): string {
  return `SELECT key, value FROM parquet_kv_metadata('${url}')`;
}

/**
 * `datajudUrls` cujo rodapé Parquet passa `validarMetadataDatajud`,
 * descartando (com aviso em `avisos`, nunca uma exceção fatal) qualquer um
 * que falhe a leitura ou a checagem -- mesma política non-fatal-per-artifact
 * de `validarMetadataDjenUrls`/`validarMetadataJurisUrls`.
 */
export async function validarMetadataDatajudUrls(
  conn: DuckDBConnectionLike,
  datajudUrls: string[],
  avisos: string[],
): Promise<string[]> {
  const validated: string[] = [];
  for (const url of datajudUrls) {
    if (datajudItemIdDaUrl(url) === null) {
      validated.push(url);
      continue;
    }
    try {
      const rows = await queryRows(conn, buildDatajudArtifactMetadataSql(url), []);
      const metadata: Record<string, string> = {};
      for (const row of rows) metadata[String(row.key)] = String(row.value);
      validarMetadataDatajud(url, metadata);
    } catch (err) {
      if (err instanceof ArtifactProvenanceError) {
        avisos.push(`Fonte 'datajud' descartou um artefato com ${err.message}`);
      } else {
        const detalhe = err instanceof Error ? err.message : String(err);
        avisos.push(
          `Fonte 'datajud' descartou um artefato sem rodapé Parquet legível: ${detalhe}`,
        );
      }
      continue;
    }
    validated.push(url);
  }
  return validated;
}

/**
 * Agrupa as URLs de arquivo_ia_url do índice por fonte, sem repetição,
 * ordenadas -- descartando (com aviso em `avisos`) qualquer uma que falhe a
 * política de artefato (`validateArtifactUrl`) ou a checagem de coerência de
 * tribunal (`validarTribunalCoerente`) -- ambas #1610.
 */
export function fonteUrls(
  rows: Array<{ fonte: string; url: string; tribunal: string }>,
  fonte: Fonte,
  avisos: string[],
): string[] {
  const urlsTribunais = new Map<string, Set<string>>();
  for (const row of rows) {
    if (row.fonte !== fonte) continue;
    if (!urlsTribunais.has(row.url)) urlsTribunais.set(row.url, new Set());
    urlsTribunais.get(row.url)!.add(row.tribunal);
  }
  const validated: string[] = [];
  for (const url of Array.from(urlsTribunais.keys()).sort()) {
    try {
      const urlValida = validateArtifactUrl(url);
      for (const tribunal of urlsTribunais.get(url)!) {
        validarTribunalCoerente(fonte, tribunal, urlValida);
      }
      validated.push(urlValida);
    } catch (err) {
      if (err instanceof ArtifactUrlError) {
        avisos.push(`Fonte '${fonte}' descartou um artefato inválido no índice: ${err.message}`);
      } else if (err instanceof ArtifactProvenanceError) {
        avisos.push(`Fonte '${fonte}' descartou um artefato com tribunal incoerente no índice: ${err.message}`);
      } else {
        throw err;
      }
    }
  }
  return validated;
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
 * Mesmo template de `causaganha.processos.service._fonte_indisponivel_aviso`
 * — extraído como função nomeada (em vez de string inline em `queryRowSafe`)
 * para que o texto do aviso seja comparável, teste a teste, com o que o
 * Python realmente produz (#1107: "fonte indisponível" precisa da mesma
 * redação observável nas duas superfícies, não só do mesmo booleano
 * `present`).
 */
export function formatFonteIndisponivelAviso(fonte: Fonte, detalhe: string): string {
  return `Fonte '${fonte}' indisponível para este processo: ${detalhe}`;
}

const FONTE_INDISPONIVEL_AVISO_PATTERN = /^Fonte '([a-z]+)' indisponível para este processo: /;

/**
 * Inverso de formatFonteIndisponivelAviso: extrai a fonte de um aviso, se o
 * aviso seguir exatamente esse formato. Usado por quem precisa saber QUAL
 * fonte falhou a partir de `ProcessoResultado.avisos` (ex.: snapshot de
 * consulta salva, #1133) sem duplicar o parsing do texto em cada chamador.
 */
export function parseFonteIndisponivelAviso(aviso: string): Fonte | null {
  const match = FONTE_INDISPONIVEL_AVISO_PATTERN.exec(aviso);
  const fonte = match?.[1];
  return fonte && (ALL_FONTES as readonly string[]).includes(fonte) ? (fonte as Fonte) : null;
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
    avisos.push(formatFonteIndisponivelAviso(fonte, detalhe));
    return null;
  }
}

/**
 * Live counterpart of `resolveDjenEqualityMode`: queries the footer of every
 * discovered DJEN file and decides the equality mode. A failing query
 * (network error, older DuckDB-WASM build without `parquet_kv_metadata`)
 * degrades to the always-safe compatible path rather than surfacing a
 * "fonte indisponível" aviso -- this is a capability probe, not a data
 * source, and the DJEN query itself still runs normally right after.
 */
async function resolveDjenEqualityModeLive(conn: DuckDBConnectionLike, djenUrls: string[]): Promise<DjenEqualityMode> {
  try {
    const rows = await queryRows(conn, buildDjenCertificationSql(djenUrls), []);
    return resolveDjenEqualityMode(
      djenUrls,
      rows.map((r) => ({ file_name: String(r.file_name), key: String(r.key), value: String(r.value) })),
    );
  } catch {
    return 'compatible';
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
  /**
   * O mesmo dossiê, validado contra o contrato OKF compartilhado (#1105) via
   * `serializeSharedCore` (#1120) — a mesma verificação que o MCP aplica do
   * lado Python, agora também sobre o retorno vivo de `buscarProcesso()`.
   */
  nucleoCompartilhado: SharedCore;
}

/**
 * Busca o dossiê unificado de um CNJ (20 dígitos) via indice_processual.parquet
 * + parquets de origem. Espelha causaganha/processos/service.py:buscar_processo
 * — não conhece FastMCP/Svelte, só DuckDB. Uma fonte de origem específica ou o
 * relatório de cobertura falhando vira lacuna vazia + aviso, nunca lança.
 *
 * indice_processual.parquet em si sendo inacessível (não apenas uma fonte
 * específica) propaga como erro — como o serviço Python, que não tem
 * alternativa: não há mais fallback para um snapshot congelado (RFC 0014 M2
 * rollout fallback, retirado após a publicação confirmada do índice, #1063).
 * O chamador (ProcessoLookup.svelte) trata a rejeição como "fonte
 * indisponível".
 */
export async function buscarProcesso(conn: DuckDBConnectionLike, digits: string): Promise<ProcessoResultado> {
  const avisos: string[] = [];
  const coberturaResult = await fetchCobertura();
  const cobertura = coberturaResult?.cobertura ?? [];
  const datasetGeradoEm = coberturaResult?.datasetGeradoEm ?? null;
  if (!coberturaResult) avisos.push(RELATORIO_INDISPONIVEL_AVISO);

  const nrProcessoMascara = formatCnj(digits);
  const indiceRows = await queryRows(conn, buildIndiceSql(), [digits]);

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
      nucleoCompartilhado: serializeSharedCore({
        encontrado: false,
        nrProcesso: digits,
        nrProcessoMascara,
        fontesPresentes: [],
        djen: AUSENTE_DJEN,
        juris: AUSENTE_JURIS,
        stj: AUSENTE_STJ,
        datajud: AUSENTE_DATAJUD,
        coberturaDataset: cobertura,
        datasetGeradoEm,
        avisos,
      }),
    };
  }

  const rowPairs = indiceRows.map((r) => ({
    fonte: String(r.fonte),
    url: String(r.arquivo_ia_url),
    tribunal: String(r.tribunal ?? ''),
  }));
  const fontes = (Array.from(new Set(rowPairs.map((r) => r.fonte))).sort() as Fonte[]).filter((f) =>
    ALL_FONTES.includes(f),
  );
  const djenUrls = await validarMetadataDjenUrls(conn, fonteUrls(rowPairs, 'djen', avisos), avisos);
  const jurisUrls = await validarMetadataJurisUrls(conn, fonteUrls(rowPairs, 'juris', avisos), avisos);
  const stjUrls = fonteUrls(rowPairs, 'stj', avisos);
  const datajudUrls = await validarMetadataDatajudUrls(
    conn,
    fonteUrls(rowPairs, 'datajud', avisos),
    avisos,
  );

  const djenEqualityMode = djenUrls.length ? await resolveDjenEqualityModeLive(conn, djenUrls) : 'compatible';
  const djenRaw = djenUrls.length
    ? await queryRowSafe(conn, 'djen', buildDjenSql(djenUrls, djenEqualityMode), [digits], avisos)
    : null;
  const jurisRaw = jurisUrls.length
    ? await queryRowSafe(conn, 'juris', buildJurisSql(jurisUrls), [digits], avisos)
    : null;
  const stjRaw = stjUrls.length ? await queryRowSafe(conn, 'stj', buildStjSql(stjUrls), [digits], avisos) : null;
  const datajudRaw = datajudUrls.length
    ? await queryRowSafe(conn, 'datajud', buildDatajudSql(datajudUrls), [digits], avisos)
    : null;

  const djen = mapDjenRow(djenRaw);
  const juris = mapJurisRow(jurisRaw);
  const stj = mapStjRow(stjRaw);
  const datajud = mapDatajudRow(datajudRaw);

  return {
    encontrado: true,
    nrProcesso: digits,
    nrProcessoMascara,
    fontes,
    djen,
    juris,
    stj,
    datajud,
    jurisUrls,
    stjUrls,
    cobertura,
    datasetGeradoEm,
    avisos,
    nucleoCompartilhado: serializeSharedCore({
      encontrado: true,
      nrProcesso: digits,
      nrProcessoMascara,
      fontesPresentes: fontes,
      djen,
      juris,
      stj,
      datajud,
      coberturaDataset: cobertura,
      datasetGeradoEm,
      avisos,
    }),
  };
}

/**
 * Busca uma página de documentos JURIS/STJ para um CNJ já resolvido por
 * buscarProcesso() — reusa `jurisUrls`/`stjUrls` descobertas ali, sem
 * reconsultar o índice. Retorna vazio sem consultar nada quando nenhuma das
 * duas fontes tem registro.
 */
export async function carregarDocumentos(
  conn: DuckDBConnectionLike,
  jurisUrls: string[],
  stjUrls: string[],
  digits: string,
  offset: number,
  pageSize: number = DOCUMENTOS_PAGE_SIZE,
): Promise<PageResult<ProcessoDocumentoRow>> {
  if (jurisUrls.length === 0 && stjUrls.length === 0) {
    return { items: [], hasMore: false };
  }
  const { sql, nParams } = buildDocumentosSql(jurisUrls, stjUrls);
  const params = [...Array(nParams).fill(digits), pageSize + 1, offset];
  const rawRows = await queryRows(conn, sql, params);
  return paginate(rawRows.map(mapDocumentoRow), pageSize);
}
