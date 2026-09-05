"""Deterministic multi-fonte fixtures shared by processo-service tests and tooling.

Used by `tests/causaganha/processos/test_service.py` and by the cross-runtime
query-plan parity harness (`scripts/processo_query_plan_fixture.py`,
`scripts/processo_query_plan_compare.py` — issue #1107) so both exercise the
exact same DJEN/JURIS/STJ/DataJud rows instead of two hand-maintained fixture
sets that can silently drift apart.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import duckdb


if TYPE_CHECKING:
    from pathlib import Path

CNJ_ALL = "00000010220248220001"
CNJ_DJEN_ONLY = "00000020320248220002"
CNJ_UNKNOWN = "00000030420248220003"

# Registered in indice_processual for 'djen', but arquivo_ia_url points at a
# parquet that is never written — a real duckdb.Error on read, distinct from
# CNJ_UNKNOWN's zero-row (never-registered) absence. Exercises #1107's
# "fonte registrada mas parquet indisponível" ≠ "CNJ ausente" distinction
# through the real query-plan parity harness (scripts/processo_query_plan_compare.py).
CNJ_SOURCE_UNAVAILABLE = "00000060720248220006"

# Not wired into indice_processual — exists only in the juris/stj source
# parquets, to exercise principal-document tie-break selection (a more
# recent SENTENÇA must lose to an older ACÓRDÃO; a more recent STJ acórdão
# must win over an older one) without touching CNJ_ALL's existing
# assertions in test_service.py (#1107 query-plan parity harness).
CNJ_TIEBREAK = "00000050620248220005"

# Matches build_fixtures()'s "report" fixture generated_at below — kept as a
# constant so callers can build deterministic "avisos == []" assertions
# instead of drifting with wall-clock time as this fixed timestamp ages past
# the 48h staleness SLO.
GERADO_EM = datetime(2026, 7, 12, 18, 0, 0, tzinfo=UTC)


def copy_to_parquet(path: Path, sql: str) -> Path:
    con = duckdb.connect()
    try:
        con.execute(f"COPY ({sql}) TO '{path}' (FORMAT PARQUET)")
    finally:
        con.close()
    return path


def build_fixtures(tmp_path: Path) -> dict[str, Path]:
    """Materialize local parquets wired through a small indice_processual.parquet.

    `indice_processual`'s `arquivo_ia_url` column points at the other local
    paths — DuckDB's `read_parquet()` accepts local paths exactly like it
    accepts IA URLs, so this exercises the same SQL the real service (and,
    for the #1107 parity harness, the same SQL the web app builds) runs
    against remote parquets, without any network access.
    """
    comunicacoes = copy_to_parquet(
        tmp_path / "comunicacoes.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}',       DATE '2024-03-01', 'TJRO'),
            ('{CNJ_ALL}',       DATE '2024-03-05', 'TJRO'),
            ('{CNJ_DJEN_ONLY}', DATE '2024-04-01', 'TJRO')
        ) AS t(numero_processo, data_disponibilizacao, tribunal)
        """,
    )
    juris = copy_to_parquet(
        tmp_path / "tjro-juris-2024.parquet",
        f"""
        SELECT * FROM (VALUES
            (1, '{CNJ_ALL}', 'ACÓRDÃO', 'Apelação', '2a Camara', 'Des. A',
             DATE '2024-01-15', 'texto um', 'https://juris/1'),
            (2, '{CNJ_TIEBREAK}', 'SENTENÇA', 'Execução', '1a Vara', 'Juiz B',
             DATE '2024-02-01', 'texto sentença mais recente', 'https://juris/2'),
            (3, '{CNJ_TIEBREAK}', 'ACÓRDÃO', 'Apelação', '3a Camara', 'Des. C',
             DATE '2024-01-01', 'texto acórdão mais antigo', 'https://juris/3')
        ) AS t(id_documento, nr_processo, tipo, classe_judicial, orgao, relator,
               data_julgamento, texto_limpo, url_portal)
        """,
    )
    stj = copy_to_parquet(
        tmp_path / "stj-acordaos.parquet",
        f"""
        SELECT * FROM (VALUES
            ('stj-1', '{CNJ_ALL}', 'REsp', 'MIN X', 'tema', 'tese', 'ementa',
             DATE '2024-05-01', DATE '2024-05-10'),
            ('stj-2', '{CNJ_TIEBREAK}', 'AgInt', 'MIN Y', 'tema antigo', 'tese antiga',
             'ementa antiga', DATE '2023-01-01', DATE '2023-01-10'),
            ('stj-3', '{CNJ_TIEBREAK}', 'REsp', 'MIN Z', 'tema recente', 'tese recente',
             'ementa recente', DATE '2024-06-01', DATE '2024-06-10')
        ) AS t(id, "numeroProcesso", "siglaClasse", "ministroRelator", tema,
               "teseJuridica", ementa, "dataDecisao", "dataPublicacao")
        """,
    )
    datajud = copy_to_parquet(
        tmp_path / "datajud-capa-tjro.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}', 'Apelacao Civel', 'Contratos', '2a Camara', 'G2',
             DATE '2024-01-10', TIMESTAMP '2024-06-01 00:00:00'),
            ('{CNJ_TIEBREAK}', 'Execução Fiscal', 'Tributário (antigo)', '1a Vara', 'G1',
             DATE '2023-01-01', TIMESTAMP '2023-06-01 00:00:00'),
            ('{CNJ_TIEBREAK}', 'Execução Fiscal', 'Tributário (recente)', '1a Vara', 'G1',
             DATE '2023-01-01', TIMESTAMP '2024-07-01 00:00:00')
        ) AS t(numero_processo, classe_nome, assuntos, orgao_julgador, grau,
               data_ajuizamento, ultima_atualizacao)
        """,
    )
    missing_djen = tmp_path / "missing-djen.parquet"  # deliberately never written
    indice = copy_to_parquet(
        tmp_path / "indice_processual.parquet",
        f"""
        SELECT * FROM (VALUES
            ('{CNJ_ALL}',       'djen',    'c1',    'TJRO', DATE '2024-03-01', '{comunicacoes}'),
            ('{CNJ_ALL}',       'djen',    'c2',    'TJRO', DATE '2024-03-05', '{comunicacoes}'),
            ('{CNJ_ALL}',       'juris',   '1',     'TJRO', DATE '2024-01-15', '{juris}'),
            ('{CNJ_ALL}',       'stj',     'stj-1', 'STJ',  DATE '2024-05-01', '{stj}'),
            ('{CNJ_ALL}',       'datajud', 'dj-1',  'TJRO', DATE '2024-06-01', '{datajud}'),
            ('{CNJ_DJEN_ONLY}', 'djen',    'c3',    'TJRO', DATE '2024-04-01', '{comunicacoes}'),
            ('{CNJ_SOURCE_UNAVAILABLE}', 'djen', 'c4', 'TJRO', DATE '2024-04-02', '{missing_djen}')
        ) AS t(numero_processo, fonte, registro_id, tribunal, data, arquivo_ia_url)
        """,
    )
    report = tmp_path / "indice_processual.report.json"
    report.write_text(
        """{
  "generated_at": "2026-07-12T18:00:00Z",
  "sources": {
    "djen": {"status": "loaded_remote", "rows": 2},
    "juris": {"status": "loaded_remote", "rows": 1},
    "stj": {"status": "loaded_remote", "rows": 1},
    "datajud": {"status": "loaded_remote", "rows": 1}
  }
}
""",
        encoding="utf-8",
    )
    return {
        "indice": indice,
        "report": report,
        "comunicacoes": comunicacoes,
        "juris": juris,
        "stj": stj,
        "datajud": datajud,
        "missing_djen": missing_djen,
    }
