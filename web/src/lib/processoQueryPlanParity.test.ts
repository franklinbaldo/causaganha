/**
 * Cross-runtime query-plan parity (issue #1107).
 *
 * `causaganha/processos/service.py` and this file's own SQL builders
 * (`buildDjenSql`, `buildJurisSql`, ...) are two hand-maintained
 * implementations of the same product semantics — nothing forces them to
 * stay in sync. This test runs both plans' SQL text through the real DuckDB
 * engine against the exact same fixture parquets (built once by
 * `scripts/processo_query_plan_fixture.py`, shared with
 * `tests/causaganha/processos/test_service.py`) via
 * `scripts/processo_query_plan_compare.py`, and asserts the row sets agree —
 * including which document DuckDB picks as "principal" for JURIS/STJ, a
 * choice driven by an `ORDER BY`/`FIRST(...)` tie-break that a unilateral
 * edit to either side could silently change.
 *
 * DuckDB-WASM (the runtime this file's SQL actually runs under in the
 * browser) and native DuckDB (used here, and by the Python side) share the
 * same SQL engine/dialect, so running this file's SQL text through native
 * DuckDB is a faithful stand-in — the point of this test is the *query
 * plan*, not the WASM binding.
 */
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import {
  buildDatajudSql,
  buildDjenSql,
  buildDocumentosSql,
  buildIndiceSql,
  buildJurisSql,
  buildStjSql,
  formatFonteIndisponivelAviso,
  mapDatajudRow,
  mapDjenRow,
  mapJurisRow,
  mapStjRow,
} from './processoCnj';

interface FixtureManifest {
  cnj_all: string;
  cnj_djen_only: string;
  cnj_unknown: string;
  cnj_tiebreak: string;
  cnj_source_unavailable: string;
  indice_url: string;
  missing_djen_url: string;
  urls: { djen: string[]; juris: string[]; stj: string[]; datajud: string[] };
}

interface QueryPlanCase {
  label: string;
  plan: 'indice' | 'djen' | 'juris' | 'stj' | 'datajud' | 'documentos';
  urls?: string[];
  jurisUrls?: string[];
  stjUrls?: string[];
  indiceUrl?: string;
  python_params: unknown[];
  web_sql: string;
  web_params: unknown[];
}

interface CompareResult {
  label: string;
  python_rows: Record<string, unknown>[];
  web_rows: Record<string, unknown>[];
  /**
   * The Python service's mapped domain view (mirroring
   * `mapDjenRow`/`mapJurisRow`/`mapStjRow`/`mapDatajudRow`'s shape) for
   * `plan`s `djen`/`juris`/`stj`/`datajud` — undefined for `indice`/`documentos`,
   * which have no single-row domain object. Populated by
   * `scripts/processo_query_plan_compare.py` (#1107 mapping-layer slice).
   */
  python_mapped?: Record<string, unknown> | null;
  /**
   * Whether raw-SQL execution of `python_sql`/`web_sql` raised a real
   * DuckDB error (a genuinely broken parquet) instead of returning rows —
   * distinct from a merely-absent CNJ, which returns zero rows without
   * raising. Populated by `scripts/processo_query_plan_compare.py`'s
   * `_safe_rows` (#1107 "fonte indisponível" ≠ "CNJ ausente" slice).
   */
  python_raised?: boolean;
  web_raised?: boolean;
  /** The `avisos` the real `_build_*` mapper collected while resolving `python_mapped`. */
  python_mapped_avisos?: string[];
}

const fixtureRoot = mkdtempSync(join(tmpdir(), 'causaganha-query-plan-parity-'));
let manifest: FixtureManifest;
let fileCounter = 0;

beforeAll(() => {
  execFileSync('uv', ['run', 'python', '../scripts/processo_query_plan_fixture.py', fixtureRoot], {
    cwd: process.cwd(),
    stdio: 'inherit',
  });
  manifest = JSON.parse(readFileSync(join(fixtureRoot, 'manifest.json'), 'utf8')) as FixtureManifest;
});

afterAll(() => rmSync(fixtureRoot, { recursive: true, force: true }));

/** `list(DISTINCT ...)` doesn't guarantee element order — sort before comparing. */
function normalizeRow(row: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(row).map(([key, value]) => [key, Array.isArray(value) ? [...value].sort() : value]),
  );
}

function runCases(cases: QueryPlanCase[]): CompareResult[] {
  fileCounter += 1;
  const casesFile = join(fixtureRoot, `cases-${fileCounter}.json`);
  const resultsFile = join(fixtureRoot, `results-${fileCounter}.json`);
  writeFileSync(casesFile, JSON.stringify({ cases }));
  execFileSync('uv', ['run', 'python', '../scripts/processo_query_plan_compare.py', casesFile, resultsFile], {
    cwd: process.cwd(),
    stdio: 'inherit',
  });
  return JSON.parse(readFileSync(resultsFile, 'utf8')) as CompareResult[];
}

describe('processo query-plan parity (#1107)', () => {
  it('DJEN/JURIS/STJ/DataJud/documentos plans agree between Python service and Web SQL', () => {
    const { cnj_all: cnjAll, cnj_djen_only: cnjDjenOnly, cnj_tiebreak: cnjTiebreak, urls } = manifest;

    const djenSql = buildDjenSql(urls.djen);
    const jurisSql = buildJurisSql(urls.juris);
    const stjSql = buildStjSql(urls.stj);
    const datajudSql = buildDatajudSql(urls.datajud);
    const { sql: documentosSql, nParams: documentosNParams } = buildDocumentosSql(urls.juris, urls.stj);
    const documentosLimitPlusOne = 11;

    const cases: QueryPlanCase[] = [
      { label: 'djen:CNJ_ALL', plan: 'djen', urls: urls.djen, python_params: [cnjAll], web_sql: djenSql, web_params: [cnjAll] },
      {
        label: 'djen:CNJ_DJEN_ONLY',
        plan: 'djen',
        urls: urls.djen,
        python_params: [cnjDjenOnly],
        web_sql: djenSql,
        web_params: [cnjDjenOnly],
      },
      { label: 'juris:CNJ_ALL', plan: 'juris', urls: urls.juris, python_params: [cnjAll], web_sql: jurisSql, web_params: [cnjAll] },
      {
        label: 'juris:CNJ_TIEBREAK',
        plan: 'juris',
        urls: urls.juris,
        python_params: [cnjTiebreak],
        web_sql: jurisSql,
        web_params: [cnjTiebreak],
      },
      { label: 'stj:CNJ_ALL', plan: 'stj', urls: urls.stj, python_params: [cnjAll], web_sql: stjSql, web_params: [cnjAll] },
      {
        label: 'stj:CNJ_TIEBREAK',
        plan: 'stj',
        urls: urls.stj,
        python_params: [cnjTiebreak],
        web_sql: stjSql,
        web_params: [cnjTiebreak],
      },
      {
        label: 'datajud:CNJ_ALL',
        plan: 'datajud',
        urls: urls.datajud,
        python_params: [cnjAll],
        web_sql: datajudSql,
        web_params: [cnjAll],
      },
      {
        label: 'datajud:CNJ_TIEBREAK',
        plan: 'datajud',
        urls: urls.datajud,
        python_params: [cnjTiebreak],
        web_sql: datajudSql,
        web_params: [cnjTiebreak],
      },
      {
        label: 'documentos:CNJ_ALL',
        plan: 'documentos',
        jurisUrls: urls.juris,
        stjUrls: urls.stj,
        python_params: [...Array(documentosNParams).fill(cnjAll), documentosLimitPlusOne],
        web_sql: documentosSql,
        web_params: [...Array(documentosNParams).fill(cnjAll), documentosLimitPlusOne, 0],
      },
    ];

    const results = runCases(cases);
    expect(results.map((r) => r.label)).toEqual(cases.map((c) => c.label));

    for (const result of results) {
      const pythonRows = result.python_rows.map(normalizeRow);
      const webRows = result.web_rows.map(normalizeRow);
      expect(webRows, `${result.label}: web plan diverges from python plan`).toEqual(pythonRows);
    }

    // #1107 acceptance: "escolha do principal JURIS/STJ ... protegida por
    // teste de paridade" — lock in the actual selected value, not just that
    // both sides produced the same (possibly-wrong) row.
    const jurisTiebreak = results.find((r) => r.label === 'juris:CNJ_TIEBREAK');
    expect(jurisTiebreak?.web_rows[0]?.orgao).toBe('3a Camara'); // older ACÓRDÃO beats newer SENTENÇA
    const stjTiebreak = results.find((r) => r.label === 'stj:CNJ_TIEBREAK');
    expect(stjTiebreak?.web_rows[0]?.relator).toBe('MIN Z'); // most recent dataDecisao wins
  });

  it('indice plan agrees between Python service and Web SQL, including the CNJ ausente case', () => {
    // Unlike every other plan above, buildIndiceSql() used to have no way to
    // target a local fixture — it always embedded the production archive.org
    // URL (#1119's own review note). Now that it accepts an override, this
    // proves the index plan itself agrees between runtimes: which fontes a
    // known CNJ resolves to (CNJ_ALL/CNJ_DJEN_ONLY), *and* that a CNJ absent
    // from the index (CNJ_UNKNOWN) comes back as zero rows on both sides —
    // the observable "CNJ ausente" signal neither service.buscar_processo nor
    // buscarProcesso() had ever been proven to agree on before this slice.
    const { cnj_all: cnjAll, cnj_djen_only: cnjDjenOnly, cnj_unknown: cnjUnknown, indice_url: indiceUrl } = manifest;
    const indiceSql = buildIndiceSql(indiceUrl);

    const cases: QueryPlanCase[] = [
      { label: 'indice:CNJ_ALL', plan: 'indice', indiceUrl, python_params: [cnjAll], web_sql: indiceSql, web_params: [cnjAll] },
      {
        label: 'indice:CNJ_DJEN_ONLY',
        plan: 'indice',
        indiceUrl,
        python_params: [cnjDjenOnly],
        web_sql: indiceSql,
        web_params: [cnjDjenOnly],
      },
      {
        label: 'indice:CNJ_UNKNOWN',
        plan: 'indice',
        indiceUrl,
        python_params: [cnjUnknown],
        web_sql: indiceSql,
        web_params: [cnjUnknown],
      },
    ];

    const results = runCases(cases);
    expect(results.map((r) => r.label)).toEqual(cases.map((c) => c.label));

    for (const result of results) {
      expect(result.web_rows, `${result.label}: web plan diverges from python plan`).toEqual(result.python_rows);
    }

    const cnjAllResult = results.find((r) => r.label === 'indice:CNJ_ALL');
    expect(cnjAllResult?.web_rows.map((r) => r.fonte).sort()).toEqual(['datajud', 'djen', 'djen', 'juris', 'stj']);
    const cnjUnknownResult = results.find((r) => r.label === 'indice:CNJ_UNKNOWN');
    expect(cnjUnknownResult?.web_rows).toEqual([]);
    expect(cnjUnknownResult?.python_rows).toEqual([]);
  });

  it('per-source mapped domain views agree between Python service and Web SQL, present and absent', () => {
    // One level above raw-row parity: #1107's acceptance list also requires
    // "datas/nulos/listas chegam iguais após normalização pelo contrato
    // público" and "fonte indisponível continua distinta de CNJ ausente" —
    // i.e. the *mapped* view (mapDjenRow/mapJurisRow/mapStjRow/mapDatajudRow
    // on the Web side, the equivalent row-to-domain-object mapping on the
    // Python side), not just the SQL row set underneath it. CNJ_UNKNOWN is
    // absent from every source fixture (unlike CNJ_DJEN_ONLY, which is
    // genuinely present in DJEN), so it doubles as the "this source has no
    // record for this CNJ" case for all four sources.
    const { cnj_all: cnjAll, cnj_unknown: cnjUnknown, urls } = manifest;

    const djenSql = buildDjenSql(urls.djen);
    const jurisSql = buildJurisSql(urls.juris);
    const stjSql = buildStjSql(urls.stj);
    const datajudSql = buildDatajudSql(urls.datajud);

    const cases: QueryPlanCase[] = [
      { label: 'mapped:djen:PRESENT', plan: 'djen', urls: urls.djen, python_params: [cnjAll], web_sql: djenSql, web_params: [cnjAll] },
      { label: 'mapped:djen:ABSENT', plan: 'djen', urls: urls.djen, python_params: [cnjUnknown], web_sql: djenSql, web_params: [cnjUnknown] },
      { label: 'mapped:juris:PRESENT', plan: 'juris', urls: urls.juris, python_params: [cnjAll], web_sql: jurisSql, web_params: [cnjAll] },
      { label: 'mapped:juris:ABSENT', plan: 'juris', urls: urls.juris, python_params: [cnjUnknown], web_sql: jurisSql, web_params: [cnjUnknown] },
      { label: 'mapped:stj:PRESENT', plan: 'stj', urls: urls.stj, python_params: [cnjAll], web_sql: stjSql, web_params: [cnjAll] },
      { label: 'mapped:stj:ABSENT', plan: 'stj', urls: urls.stj, python_params: [cnjUnknown], web_sql: stjSql, web_params: [cnjUnknown] },
      {
        label: 'mapped:datajud:PRESENT',
        plan: 'datajud',
        urls: urls.datajud,
        python_params: [cnjAll],
        web_sql: datajudSql,
        web_params: [cnjAll],
      },
      {
        label: 'mapped:datajud:ABSENT',
        plan: 'datajud',
        urls: urls.datajud,
        python_params: [cnjUnknown],
        web_sql: datajudSql,
        web_params: [cnjUnknown],
      },
    ];

    const results = runCases(cases);
    const byLabel = new Map(results.map((r) => [r.label, r]));

    const mappers = {
      djen: mapDjenRow,
      juris: mapJurisRow,
      stj: mapStjRow,
      datajud: mapDatajudRow,
    } as const;

    for (const fonte of ['djen', 'juris', 'stj', 'datajud'] as const) {
      const presentResult = byLabel.get(`mapped:${fonte}:PRESENT`);
      const absentResult = byLabel.get(`mapped:${fonte}:ABSENT`);
      const webPresent = mappers[fonte](presentResult?.web_rows[0] ?? null);
      const webAbsent = mappers[fonte](absentResult?.web_rows[0] ?? null);

      expect(webPresent.present, `${fonte}: expected PRESENT case to resolve present=true`).toBe(true);
      expect(webAbsent.present, `${fonte}: expected ABSENT case to resolve present=false`).toBe(false);

      expect(presentResult?.python_mapped, `${fonte}: mapped view diverges from Python (present case)`).toEqual(
        webPresent,
      );
      expect(absentResult?.python_mapped, `${fonte}: mapped view diverges from Python (absent case)`).toEqual(
        webAbsent,
      );
    }
  });

  it('fonte registrada mas parquet indisponível é distinta de CNJ ausente, nas duas superfícies (#1107)', () => {
    // #1107's own acceptance criteria list "fonte indisponível continua
    // distinta de CNJ ausente nas duas superfícies" — already true within
    // each runtime's own separate unit tests (test_service.py's
    // test_one_source_parquet_unreachable_is_partial_not_fatal vs
    // test_not_found_still_carries_cobertura; processoCnj.test.ts's
    // "isolates a single source failure" vs "returns encontrado=false"),
    // but never cross-checked against the same fixture the way this file's
    // other tests already do for PRESENT/ABSENT. This closes that gap.
    const { cnj_source_unavailable: cnjUnavailable, cnj_unknown: cnjAbsent, missing_djen_url: missingDjenUrl, urls } =
      manifest;

    const brokenSql = buildDjenSql([missingDjenUrl]);
    const healthySql = buildDjenSql(urls.djen);

    const cases: QueryPlanCase[] = [
      {
        label: 'djen:UNAVAILABLE',
        plan: 'djen',
        urls: [missingDjenUrl],
        python_params: [cnjUnavailable],
        web_sql: brokenSql,
        web_params: [cnjUnavailable],
      },
      {
        label: 'djen:ABSENT',
        plan: 'djen',
        urls: urls.djen,
        python_params: [cnjAbsent],
        web_sql: healthySql,
        web_params: [cnjAbsent],
      },
    ];

    const results = runCases(cases);
    const unavailable = results.find((r) => r.label === 'djen:UNAVAILABLE')!;
    const absent = results.find((r) => r.label === 'djen:ABSENT')!;

    // Raw-SQL execution against a genuinely broken parquet raises identically
    // on both engines (native DuckDB standing in for DuckDB-WASM — see this
    // file's header comment on why that substitution is faithful here).
    expect(unavailable.python_raised, 'python raw SQL should fail against a missing parquet').toBe(true);
    expect(unavailable.web_raised, 'web raw SQL should fail against a missing parquet').toBe(true);

    // A CNJ merely absent from a healthy parquet never raises on either
    // side — a zero-row result, not an error. Different failure mode
    // entirely from the broken-parquet case above.
    expect(absent.python_raised, 'python raw SQL should not fail for an absent CNJ').toBe(false);
    expect(absent.web_raised, 'web raw SQL should not fail for an absent CNJ').toBe(false);

    // The real production mapper (_build_djen — not the isolated raw SQL
    // above) never lets that failure propagate: it degrades to
    // present=false plus exactly one fonte-specific aviso. This is the
    // "indisponível" signal that must survive to the public dossiê.
    expect(unavailable.python_mapped).toMatchObject({ present: false });
    expect(unavailable.python_mapped_avisos).toHaveLength(1);
    const [avisoIndisponivel] = unavailable.python_mapped_avisos!;
    expect(avisoIndisponivel).toMatch(/^Fonte 'djen' indisponível para este processo: /);

    // The absent case maps to the exact same present=false shape, but with
    // NO fonte-specific aviso at all — the distinguishing signal #1107
    // requires to be preserved, not conflated, across runtimes.
    expect(absent.python_mapped).toMatchObject({ present: false });
    expect(absent.python_mapped_avisos).toEqual([]);

    // The wording itself must not have drifted between runtimes either:
    // round-trip the exception detail Python actually captured through the
    // Web side's own aviso formatter and confirm it reproduces the exact
    // same string Python produced.
    const detalhe = avisoIndisponivel.replace(/^Fonte 'djen' indisponível para este processo: /, '');
    expect(formatFonteIndisponivelAviso('djen', detalhe)).toBe(avisoIndisponivel);
  });
});
