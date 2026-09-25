"""Tests for causaganha.processos.service.buscar_processo (RFC 0014 M2).

Fixtures are hand-built local parquets wired together through a small
indice_processual.parquet whose `arquivo_ia_url` column points at those local
paths — DuckDB's `read_parquet()` accepts local paths exactly like it accepts
IA URLs, so this exercises the same SQL the real service runs against remote
parquets, without any network access.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import duckdb
import pytest
import respx

from causaganha.processos import service
from causaganha.processos.models import CnjInvalidoError, FonteCobertura
from causaganha.processos.query_plan_fixtures import (
    CNJ_ALL,
    CNJ_DJEN_ONLY,
    CNJ_UNKNOWN,
    GERADO_EM,
    build_fixtures,
    copy_to_parquet,
)


if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def fixtures(tmp_path: Path) -> dict[str, Path]:
    return build_fixtures(tmp_path)


def test_multi_fonte_dossier(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=GERADO_EM,
    )

    assert result.encontrado is True
    assert result.nr_processo == CNJ_ALL
    assert result.nr_processo_mascara == "0000001-02.2024.8.22.0001"
    assert result.fontes_presentes == ["datajud", "djen", "juris", "stj"]
    assert result.avisos == []
    assert result.dataset_gerado_em == "2026-07-12T18:00:00Z"

    assert result.djen.n_publicacoes == 2
    assert result.djen.primeira_publicacao == "2024-03-01"
    assert result.djen.ultima_publicacao == "2024-03-05"
    assert result.djen.tribunais == ["TJRO"]

    assert result.juris.n_documentos == 1
    assert result.juris.orgao == "2a Camara"
    assert result.juris.relator == "Des. A"
    assert result.juris.url == "https://juris/1"

    assert result.stj.id == "stj-1"
    assert result.stj.classe == "REsp"
    assert result.stj.data_decisao == "2024-05-01"

    assert result.datajud.classe_oficial == "Apelacao Civel"
    assert result.datajud.assuntos == "Contratos"

    assert [d.fonte for d in result.documentos] == ["stj", "juris"]  # data DESC
    assert result.documentos_truncados is False


def test_single_fonte_dossier_leaves_other_fields_none(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_DJEN_ONLY, indice_url=str(fixtures["indice"]), report_url=str(fixtures["report"])
    )

    assert result.encontrado is True
    assert result.fontes_presentes == ["djen"]
    assert result.djen is not None
    assert result.juris is None
    assert result.stj is None
    assert result.datajud is None
    assert result.documentos == []
    assert result.documentos_truncados is False


def test_not_found_still_carries_cobertura(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_UNKNOWN,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=GERADO_EM,
    )

    assert result.encontrado is False
    assert result.nr_processo == CNJ_UNKNOWN
    assert result.fontes_presentes == []
    assert result.dataset_gerado_em == "2026-07-12T18:00:00Z"
    assert {c.fonte for c in result.cobertura_dataset} == {"djen", "juris", "stj", "datajud"}
    assert result.avisos == []


def test_fresh_snapshot_has_no_staleness_aviso(fixtures: dict[str, Path]) -> None:
    """dataset_gerado_em within the 48h SLO (docs/SERVICE_OBJECTIVES.md) is silent."""
    quase_48h_depois = GERADO_EM + timedelta(hours=47)
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=quase_48h_depois,
    )

    assert result.avisos == []


def test_stale_snapshot_warns_and_points_to_live_state(fixtures: dict[str, Path]) -> None:
    """A snapshot far older than the 48h SLO must not silently look current.

    Mirrors issue #891's staleness rule: "não confundir 'o processo parou'
    com 'a cópia parou'" — an old dataset_gerado_em must surface as an
    explicit warning pointing at the live-state route, not be silent.
    """
    tres_dias_depois = GERADO_EM + timedelta(days=3)
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=tres_dias_depois,
    )

    assert len(result.avisos) == 1
    aviso = result.avisos[0]
    assert "48" in aviso
    assert "processo_estado" in aviso


def test_stale_snapshot_also_warns_when_processo_not_found(fixtures: dict[str, Path]) -> None:
    """Staleness is a property of the snapshot, independent of this CNJ's hit/miss."""
    tres_dias_depois = GERADO_EM + timedelta(days=3)
    result = service.buscar_processo(
        CNJ_UNKNOWN,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
        agora=tres_dias_depois,
    )

    assert result.encontrado is False
    assert any("processo_estado" in a for a in result.avisos)


def test_missing_report_has_no_staleness_aviso_beyond_its_own(
    fixtures: dict[str, Path],
) -> None:
    """No dataset_gerado_em to compare against — never fabricate a staleness claim."""
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["indice"].parent / "does-not-exist.report.json"),
    )

    assert result.avisos == [service._RELATORIO_INDISPONIVEL_AVISO]


def test_report_fetch_follows_archive_org_redirect(fixtures: dict[str, Path]) -> None:
    """`archive.org/download/...` 302-redirects to a datanode host (#1042 live smoke).

    A real end-to-end check against the published `indice_processual.report.json`
    found this: `_fetch_text` calls `httpx.get` without `follow_redirects=True`,
    so on the real (redirecting) URL the coverage report silently fails to
    parse -- `dataset_gerado_em`/`cobertura_dataset` come back empty and the
    "relatório indisponível" warning fires even though the report is reachable
    and well-formed. The Web side (`web/src/lib/processoCnj.ts`) uses `fetch()`,
    which follows redirects by default, so MCP and Web diverged on freshness
    for the exact same published artifact.
    """
    report_url = "https://archive.org/download/causaganha-dashboard/indice_processual.report.json"
    redirect_target = "https://ia801504.us.archive.org/33/items/causaganha-dashboard/indice_processual.report.json"
    payload = {
        "generated_at": GERADO_EM.isoformat(),
        "sources": {
            "djen": {"status": "loaded_remote", "rows": 2},
            "juris": {"status": "loaded_remote", "rows": 1},
            "stj": {"status": "loaded_remote", "rows": 1},
            "datajud": {"status": "loaded_remote", "rows": 1},
        },
    }

    with respx.mock(assert_all_called=True) as router:
        router.get(report_url).respond(302, headers={"Location": redirect_target})
        router.get(redirect_target).respond(200, json=payload)

        result = service.buscar_processo(
            CNJ_ALL,
            indice_url=str(fixtures["indice"]),
            report_url=report_url,
            agora=GERADO_EM + timedelta(hours=1),
        )

    assert result.dataset_gerado_em == GERADO_EM.isoformat()
    assert result.cobertura_dataset != []
    assert result.avisos == []


def test_invalid_cnj_raises_before_touching_any_parquet() -> None:
    with pytest.raises(CnjInvalidoError):
        service.buscar_processo(
            "123",
            indice_url="/nonexistent/indice_processual.parquet",
            report_url="/nonexistent.json",
        )


def test_missing_report_is_partial_not_fatal(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["indice"].parent / "does-not-exist.report.json"),
    )

    assert result.encontrado is True  # the processo itself still resolves
    assert result.cobertura_dataset == []
    assert result.dataset_gerado_em is None
    assert any("relatório de cobertura" in a.lower() for a in result.avisos)


def test_malformed_report_is_partial_not_fatal(fixtures: dict[str, Path], tmp_path: Path) -> None:
    """A syntactically-valid report whose `sources` entries lack `status`/`rows`.

    Before the fix, `_carregar_cobertura`'s list comprehension read
    `fonte["status"]`/`fonte["rows"]` outside its try/except, so a report that
    parses as valid JSON but has the wrong shape raised an uncaught KeyError
    instead of degrading -- contradicting the module docstring's "None quando
    indisponível/ilegível" contract. Mirrors the Web twin
    (`web/src/lib/processoCnj.ts::fetchCobertura`), which already defaults a
    missing `status`/`rows` to `'unknown'`/`0` per-source rather than dropping
    the whole report or raising.
    """
    malformed_report = tmp_path / "malformed.report.json"
    malformed_report.write_text('{"sources": {"djen": {"status": "loaded_remote"}}}')

    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(malformed_report),
    )

    assert result.encontrado is True  # the processo itself still resolves
    assert result.cobertura_dataset == [
        FonteCobertura(fonte="djen", status="loaded_remote", registros=0)
    ]
    assert result.avisos == []  # report itself loaded fine, just one field defaulted


def test_report_rejects_boolean_rows_instead_of_counting_as_one(
    fixtures: dict[str, Path], tmp_path: Path
) -> None:
    """`"rows": true` must default to 0, not survive as a fabricated count of 1.

    `bool` is a subclass of `int` in Python, so a naive `isinstance(value, int)`
    guard accepts `True`/`False` as valid row counts -- and the public Pydantic
    contract then coerces `True` to `1`, publishing a fabricated record count
    for a field that was never a real integer (#1454 review).
    """
    report = tmp_path / "boolean_rows.report.json"
    report.write_text('{"sources": {"djen": {"status": "loaded_remote", "rows": true}}}')

    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(report),
    )

    assert result.cobertura_dataset == [
        FonteCobertura(fonte="djen", status="loaded_remote", registros=0)
    ]


def test_report_with_non_object_sources_is_unavailable_not_empty(
    fixtures: dict[str, Path], tmp_path: Path
) -> None:
    """A present-but-wrong-typed `sources` (null/array/string) is unavailable.

    Before this fix, a non-dict `sources` value silently became an empty
    mapping and buscar_processo returned a *successful* empty coverage list
    with no warning -- indistinguishable from a report that genuinely lists
    zero sources. It must instead take the same 'relatório indisponível' path
    as a missing file or invalid JSON syntax (#1454 review).
    """
    report = tmp_path / "non_object_sources.report.json"
    report.write_text('{"sources": ["not", "a", "mapping"]}')

    result = service.buscar_processo(
        CNJ_ALL,
        indice_url=str(fixtures["indice"]),
        report_url=str(report),
    )

    assert result.cobertura_dataset == []
    assert result.dataset_gerado_em is None
    assert any("relatório de cobertura" in a.lower() for a in result.avisos)


def test_one_source_parquet_unreachable_is_partial_not_fatal(
    fixtures: dict[str, Path], tmp_path: Path
) -> None:
    """A source's own parquet failing must not take down the whole dossiê.

    Mirrors reconcile_processos.py's own philosophy (a corrupted/unreachable
    source parquet degrades to a warning, never crashes the run) — the
    module docstring promises the same for buscar_processo, exercised here
    against DJEN specifically (its arquivo_ia_url points nowhere).
    """
    missing = tmp_path / "missing.parquet"
    broken_indice = copy_to_parquet(
        tmp_path / "indice_broken.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}', 'djen',    'c1',    'TJRO', DATE '2024-03-01', '{missing}'),
            ('{CNJ_ALL}', 'juris',   '1',     'TJRO', DATE '2024-01-15', '{fixtures["juris"]}'),
            ('{CNJ_ALL}', 'stj',     'stj-1', 'STJ',  DATE '2024-05-01', '{fixtures["stj"]}'),
            ('{CNJ_ALL}', 'datajud', 'dj-1',  'TJRO', DATE '2024-06-01', '{fixtures["datajud"]}')
        ) AS t(numero_processo, fonte, registro_id, tribunal, data, arquivo_ia_url)
        """,
    )

    result = service.buscar_processo(
        CNJ_ALL, indice_url=str(broken_indice), report_url=str(fixtures["report"])
    )

    assert result.encontrado is True
    assert result.djen is None  # the broken source's gap is empty, not a crash
    assert any("djen" in a.lower() for a in result.avisos)
    # unaffected sources still load normally
    assert result.juris is not None
    assert result.stj is not None
    assert result.datajud is not None


def test_indice_processual_itself_unreachable_propagates() -> None:
    """Unlike a source parquet, the index itself failing has no partial answer."""
    with pytest.raises(duckdb.Error):
        service.buscar_processo(
            CNJ_ALL,
            indice_url="/nonexistent/indice_processual.parquet",
            report_url="/nonexistent.report.json",
        )


def test_incluir_documentos_false_skips_the_documentos_query(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        incluir_documentos=False,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
    )

    assert result.documentos == []
    assert result.documentos_truncados is False
    # the per-fonte summaries are unaffected — only the documents list is skipped
    assert result.juris is not None
    assert result.stj is not None


def test_limite_documentos_truncates_and_flags_it(fixtures: dict[str, Path]) -> None:
    result = service.buscar_processo(
        CNJ_ALL,
        limite_documentos=1,
        indice_url=str(fixtures["indice"]),
        report_url=str(fixtures["report"]),
    )

    assert len(result.documentos) == 1
    assert result.documentos[0].fonte == "stj"  # most recent by data DESC
    assert result.documentos_truncados is True


def _spy_on_connect(monkeypatch: pytest.MonkeyPatch) -> list[duckdb.DuckDBPyConnection]:
    """Wraps duckdb.connect so the test can inspect the connection afterwards."""
    captured: list[duckdb.DuckDBPyConnection] = []
    real_connect = duckdb.connect

    def _spy(*args: object, **kwargs: object) -> duckdb.DuckDBPyConnection:
        con = real_connect(*args, **kwargs)
        captured.append(con)
        return con

    monkeypatch.setattr(service.duckdb, "connect", _spy)
    return captured


def test_connection_is_closed_on_success(
    fixtures: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A long-running MCP server calls buscar_processo repeatedly — a leaked
    DuckDBPyConnection per call would accumulate handles/memory over time.
    """
    captured = _spy_on_connect(monkeypatch)

    service.buscar_processo(
        CNJ_ALL, indice_url=str(fixtures["indice"]), report_url=str(fixtures["report"])
    )

    assert len(captured) == 1
    with pytest.raises(duckdb.Error):
        captured[0].execute("SELECT 1")  # closed connections refuse queries


def test_connection_is_closed_when_indice_itself_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The one fatal path (index unreachable) must still close the connection."""
    captured = _spy_on_connect(monkeypatch)

    with pytest.raises(duckdb.Error):
        service.buscar_processo(
            CNJ_ALL,
            indice_url="/nonexistent/indice_processual.parquet",
            report_url="/nonexistent.report.json",
        )

    assert len(captured) == 1
    with pytest.raises(duckdb.Error):
        captured[0].execute("SELECT 1")


class TestValidateArtifactUrl:
    """Issue #1610: `arquivo_ia_url` values come straight from
    `indice_processual.parquet`, a canonical manifest artifact interpolated
    as-is into `read_parquet([...])` by `_url_list_sql`. A compromised
    manifest must not be able to redirect DuckDB's fetch destination or break
    out of that naive string-literal embedding.
    """

    @pytest.mark.parametrize(
        "url",
        [
            "https://archive.org/download/tjro-juris-2024/tjro-juris-2024.parquet",
            "https://archive.org/download/causaganha-dashboard/indice_processual.parquet",
        ],
    )
    def test_valid_archive_org_urls_pass(self, url: str) -> None:
        assert service._validate_artifact_url(url) == url

    def test_local_path_without_scheme_passes(self, tmp_path: Path) -> None:
        local = str(tmp_path / "fixture.parquet")
        assert service._validate_artifact_url(local) == local

    def test_embedded_quote_is_rejected(self, tmp_path: Path) -> None:
        malicious = str(tmp_path / "evil.parquet") + "'; ATTACH '/etc/passwd' AS pwn; --"
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url(malicious)

    def test_http_scheme_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url("http://archive.org/download/x/x.parquet")

    def test_file_scheme_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url("file:///etc/passwd")

    def test_foreign_host_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url("https://evil.example/download/x/x.parquet")

    def test_query_string_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url(
                "https://archive.org/download/x/x.parquet?redirect=https://evil.example"
            )

    def test_fragment_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url("https://archive.org/download/x/x.parquet#frag")

    def test_non_parquet_path_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url("https://archive.org/download/x/x.json")

    def test_path_outside_download_prefix_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactUrlError):
            service._validate_artifact_url("https://archive.org/metadata/x/x.parquet")


class TestTribunalCoerenteComUrl:
    """Issue #1610 (TM-04): a manifest row's `tribunal` column and its
    `arquivo_ia_url` are two independent claims about the same fact. A
    compromised or corrupted `indice_processual.parquet` could keep the URL
    policy-valid (issue #1610's URL half) while pointing a row labeled one
    tribunal at another tribunal's IA item — the "controle de significado"
    threat from the issue body, where wrong attribution never needs a bad
    fetch destination to succeed.
    """

    @pytest.mark.parametrize(
        ("fonte", "url", "esperado"),
        [
            ("djen", "https://archive.org/download/djen-tjro-2024/comunicacoes.parquet", "tjro"),
            ("djen", "https://archive.org/download/djen-tjsp-2025/comunicacoes.parquet", "tjsp"),
            (
                "datajud",
                "https://archive.org/download/datajud-tjro/datajud-capa-tjro.parquet",
                "tjro",
            ),
        ],
    )
    def test_tribunal_extracted_from_partitioned_sources(
        self, fonte: str, url: str, esperado: str
    ) -> None:
        assert service._tribunal_da_url(fonte, url) == esperado

    @pytest.mark.parametrize(
        ("fonte", "url"),
        [
            ("juris", "https://archive.org/download/tjro-juris-2024/tjro-juris-2024.parquet"),
            (
                "stj",
                "https://archive.org/download/stj-acordaos-primeira-secao/stj-acordaos.parquet",
            ),
        ],
    )
    def test_none_for_sources_not_partitioned_by_tribunal(self, fonte: str, url: str) -> None:
        assert service._tribunal_da_url(fonte, url) is None

    def test_none_for_local_test_path(self, tmp_path: Path) -> None:
        assert service._tribunal_da_url("djen", str(tmp_path / "comunicacoes.parquet")) is None

    def test_matching_tribunal_case_insensitive_passes(self) -> None:
        service._validar_tribunal_coerente(
            "djen", "TJRO", "https://archive.org/download/djen-tjro-2024/comunicacoes.parquet"
        )

    def test_mismatched_tribunal_is_rejected(self) -> None:
        with pytest.raises(service.ArtifactProvenanceError):
            service._validar_tribunal_coerente(
                "djen",
                "TJSP",
                "https://archive.org/download/djen-tjro-2024/comunicacoes.parquet",
            )

    def test_unverifiable_url_does_not_raise(self, tmp_path: Path) -> None:
        service._validar_tribunal_coerente("juris", "TJRO", str(tmp_path / "juris.parquet"))


def test_poisoned_manifest_tribunal_degrades_source_instead_of_trusting(tmp_path: Path) -> None:
    """The TM-04 half of issue #1610: `indice_processual.parquet` declares one
    tribunal for a `datajud` row while `arquivo_ia_url` itself names another
    tribunal's IA item. This must degrade to an aviso, like a policy-invalid
    URL, instead of `buscar_processo` trusting whichever tribunal string won.
    """
    swapped = "https://archive.org/download/datajud-tjsp/datajud-capa-tjsp.parquet"
    con = duckdb.connect()
    try:
        indice = tmp_path / "indice_processual.parquet"
        con.execute(
            f"""
            COPY (
                SELECT ? AS numero_processo, 'datajud' AS fonte, 'x' AS registro_id,
                    'TJRO' AS tribunal, DATE '2024-01-01' AS data, ? AS arquivo_ia_url
            ) TO '{indice}' (FORMAT PARQUET)
            """,
            [CNJ_ALL, swapped],
        )
    finally:
        con.close()
    report = tmp_path / "indice_processual.report.json"
    report.write_text('{"generated_at": "2026-07-12T18:00:00Z", "sources": {}}', encoding="utf-8")

    result = service.buscar_processo(CNJ_ALL, indice_url=str(indice), report_url=str(report))

    assert result.encontrado is True
    assert result.datajud is None
    # Must be rejected by the provenance check itself -- before any
    # `read_parquet` is attempted against the mismatched URL -- not merely
    # degrade because the fabricated archive.org path happens to be
    # unreachable from this test environment.
    assert any("incoerente" in aviso.lower() for aviso in result.avisos)
    assert not any("indispon" in aviso.lower() for aviso in result.avisos)
    """The exact threat issue #1610 describes: a compromised
    `indice_processual.parquet` points `arquivo_ia_url` at an unexpected host.
    The source must degrade to an aviso, like any other unavailable source,
    instead of `read_parquet` ever seeing that URL.
    """
    malicious = "https://evil.example/download/x/x.parquet"
    con = duckdb.connect()
    try:
        indice = tmp_path / "indice_processual.parquet"
        con.execute(
            f"""
            COPY (
                SELECT ? AS numero_processo, 'djen' AS fonte, 'x' AS registro_id,
                    'TJRO' AS tribunal, DATE '2024-01-01' AS data, ? AS arquivo_ia_url
            ) TO '{indice}' (FORMAT PARQUET)
            """,
            [CNJ_ALL, malicious],
        )
    finally:
        con.close()
    report = tmp_path / "indice_processual.report.json"
    report.write_text('{"generated_at": "2026-07-12T18:00:00Z", "sources": {}}', encoding="utf-8")

    result = service.buscar_processo(CNJ_ALL, indice_url=str(indice), report_url=str(report))

    assert result.encontrado is True
    assert result.djen is None
    assert any("djen" in aviso.lower() for aviso in result.avisos)
