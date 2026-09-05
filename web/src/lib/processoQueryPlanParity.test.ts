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
import { buildDatajudSql, buildDjenSql, buildDocumentosSql, buildJurisSql, buildStjSql } from './processoCnj';

interface FixtureManifest {
  cnj_all: string;
  cnj_djen_only: string;
  cnj_tiebreak: string;
  urls: { djen: string[]; juris: string[]; stj: string[]; datajud: string[] };
}

interface QueryPlanCase {
  label: string;
  plan: 'djen' | 'juris' | 'stj' | 'datajud' | 'documentos';
  urls?: string[];
  jurisUrls?: string[];
  stjUrls?: string[];
  python_params: unknown[];
  web_sql: string;
  web_params: unknown[];
}

interface CompareResult {
  label: string;
  python_rows: Record<string, unknown>[];
  web_rows: Record<string, unknown>[];
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
});
