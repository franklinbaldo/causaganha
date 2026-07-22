#!/usr/bin/env python3
"""Execute .qmd query files against the manifest and emit JSON.

Purpose:  Turn the frontend's .qmd query contracts into the JSON datasets it loads.
Problem:  The web app declares its data needs as .qmd files; something must execute
          them against the manifest without depending on the Quarto binary.
Strategy: Scan web/src/queries/*.qmd, parse the frontmatter (output/format) + SQL
          fence, run each against the manifest via DuckDB, and write JSON under
          web/public — staying Quarto-compatible for later HTML rendering.
Status:   production — runs in deploy-web.yml (--strict), test.yml (--check) and
          update-catalog.yml; the canonical manifest→frontend data path (see
          web/src/queries/README.md).

Modes (RFC 0007 — fail-loud data contracts):
  (default)   render all contracts; missing optional sources warn, nothing fatal.
  --check     static validation, no network: frontmatter fields + SQL executed
              against synthetic empty schemas derived from the same view registry
              the render uses. Exit 1 listing every invalid .qmd.
  --strict    render; a required (non-``optional``) contract that cannot produce
              its JSON fails the run with exit 1. Used by deploy-web.yml.

Frontmatter contract:
  output: /data/foo.json    # path under web/public (must start with /data/)
  format: array | object    # array of rows OR single row object
  optional: true            # optional contract — data source may be absent

Data sources available in SQL: see VIEW_SPECS below.
"""

from __future__ import annotations

import contextlib

# Safely reconfigure standard output and standard error encoding error handling on Windows
import sys


for stream in (sys.stdout, sys.stderr):
    if stream and stream.encoding and stream.encoding.lower() != "utf-8":
        with contextlib.suppress(AttributeError):
            stream.reconfigure(errors="replace")

import argparse
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from collections.abc import Callable

import duckdb
import yaml


ROOT = Path(__file__).resolve().parent.parent

# Running as `python scripts/render_queries.py` puts scripts/ (not the repo
# root) on sys.path — add the root so `scripts.reconcile_processos` imports.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datajud.archive import CAPA_SCHEMA as _DATAJUD_CAPA_SCHEMA
from djen_backup.manifest import HEADER as _MANIFEST_HEADER
from tjro_juris.service import _PARQUET_SCHEMA as _TJRO_JURIS_SCHEMA


QUERIES_DIR = ROOT / "web" / "src" / "queries"
PUBLIC_DIR = ROOT / "web" / "public"
MANIFEST_PARQUET_URL = "https://archive.org/download/causaganha-dashboard/sync-manifest.parquet"
LOCAL_MANIFEST_PARQUET = ROOT / "data" / "sync-manifest.parquet"

# Local dev/CI fallback: exported parquet snapshots from the ratings pipeline.
# Views are only registered when the files exist; contracts that depend on
# them declare `optional: true` and are skipped with a named warning.
DEV_RATINGS_DIR = ROOT / "data" / "parquets"

# Optional parquet views for STJ and TJRO JURIS corpora.
# When the consolidated parquets are present locally (after running the
# respective ingestão pipelines), these views power stj_* and juris_* queries.
_STJ_PARQUET = ROOT / "data" / "stj" / "stj-acordaos.parquet"
_STJ_PARQUET_IA_URL = (
    "https://archive.org/download/stj-acordaos-primeira-secao/stj-acordaos.parquet"
)

# RFC 0014 M2: the reconciler no longer publishes a wide processos_unificados/
# processo_documentos parquet — indice_processual.parquet is the sole
# canonical cross-source artifact. `processos_unificados`/`processo_documentos`
# survive here only as VIEW NAMES, computed on the fly by aggregating the raw
# per-source views (comunicacoes/tjro_juris/acordaos/datajud_capa) — the exact
# aggregation SQL scripts/reconcile_processos.py used to run, just relocated
# here since this is now the only remaining consumer of that shape. This keeps
# every existing .qmd contract (e.g. processos_multi_fonte.qmd) unchanged.
_INDICE_PROCESSUAL_PARQUET = ROOT / "data" / "indice_processual.parquet"
_INDICE_PROCESSUAL_IA_URL = (
    "https://archive.org/download/causaganha-dashboard/indice_processual.parquet"
)

# DDL that produces the catalog tables exported as lawyer_ratings.parquet /
# ratings_history.parquet (scripts/pipeline/export_ratings.py) — reused as the
# synthetic schema source for --check.
_CATALOG_SCHEMA_SQL = ROOT / "src" / "causaganha" / "storage" / "schema.sql"

SQL_FENCE_RE = re.compile(
    r"```\s*\{\s*sql[^}]*\}\s*\n(.*?)\n```",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_ALLOWED_FORMATS = ("array", "object")
_OUTPUT_PREFIX = "/data/"


def parse_qmd(path: Path) -> tuple[dict[str, Any], str]:
    """Extract frontmatter dict and first SQL block from a .qmd file."""
    text = path.read_text(encoding="utf-8")

    fm_match = FRONTMATTER_RE.match(text)
    if not fm_match:
        msg = f"{path}: missing YAML frontmatter"
        raise ValueError(msg)
    frontmatter = yaml.safe_load(fm_match.group(1)) or {}

    sql_match = SQL_FENCE_RE.search(text)
    if not sql_match:
        msg = f"{path}: no ```{{sql}}``` code block"
        raise ValueError(msg)
    sql = sql_match.group(1).strip()

    return frontmatter, sql


def validate_frontmatter(frontmatter: dict[str, Any]) -> list[str]:
    """Return a list of contract violations in the frontmatter (empty = valid)."""
    errors: list[str] = []

    output = frontmatter.get("output")
    if not output:
        errors.append("missing required frontmatter field 'output'")
    elif not str(output).startswith(_OUTPUT_PREFIX):
        errors.append(f"'output' must start with '{_OUTPUT_PREFIX}' (got {output!r})")

    fmt = frontmatter.get("format")
    if not fmt:
        errors.append("missing required frontmatter field 'format'")
    elif fmt not in _ALLOWED_FORMATS:
        errors.append(f"'format' must be one of {list(_ALLOWED_FORMATS)} (got {fmt!r})")

    if not isinstance(frontmatter.get("optional", False), bool):
        errors.append("'optional' must be a boolean")

    return errors


def _try_download_parquet(url: str, dest: Path, label: str) -> Path | None:
    """Download parquet from IA if not present locally; return path or None."""
    if dest.exists():
        print(f"Using local {label}: {dest}")
        return dest
    print(f"Downloading {label} from IA: {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            dest.write_bytes(resp.read())
    except OSError as exc:
        print(f"  WARNING: could not download {label} — {exc}", file=sys.stderr)
        return None
    return dest


# ── processos_unificados/processo_documentos aggregation (RFC 0014 M2) ─────────
# Moved verbatim from scripts/reconcile_processos.py, which no longer computes
# this shape — it publishes the thin indice_processual.parquet instead. This
# is now the only place that needs the collapsed/wide view (for .qmd
# contracts like processos_multi_fonte.qmd that predate the index), so it
# lives here rather than duplicated across two files.

_DJEN_AGG_SQL = """
SELECT
    regexp_replace(numero_processo, '[^0-9]', '', 'g') AS nr_processo,
    MIN(data_disponibilizacao)::DATE  AS djen_primeira_pub,
    MAX(data_disponibilizacao)::DATE  AS djen_ultima_pub,
    COUNT(*)::INTEGER                 AS djen_n_publicacoes,
    list(DISTINCT tribunal)           AS djen_tribunais
FROM comunicacoes
WHERE length(regexp_replace(numero_processo, '[^0-9]', '', 'g')) = 20
GROUP BY nr_processo
"""

_JURIS_AGG_SQL = """
WITH cleaned AS (
    SELECT
        regexp_replace(nr_processo, '[^0-9]', '', 'g') AS nr_processo,
        id_documento,
        tipo,
        data_julgamento,
        orgao,
        relator,
        classe_judicial,
        url_portal
    FROM tjro_juris
    WHERE length(regexp_replace(nr_processo, '[^0-9]', '', 'g')) = 20
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY nr_processo
            ORDER BY
                CASE tipo
                    WHEN 'ACÓRDÃO' THEN 1
                    WHEN 'SENTENÇA' THEN 2
                    ELSE 9
                END,
                data_julgamento DESC NULLS LAST
        ) AS rn
    FROM cleaned
),
principal AS (
    SELECT * FROM ranked WHERE rn = 1
),
agg AS (
    SELECT
        nr_processo,
        COUNT(*)::INTEGER        AS juris_n_documentos,
        list(DISTINCT tipo)      AS juris_tipos,
        MAX(data_julgamento)     AS juris_data_julgamento
    FROM cleaned
    GROUP BY nr_processo
)
SELECT
    agg.nr_processo,
    agg.juris_n_documentos,
    agg.juris_tipos,
    agg.juris_data_julgamento::DATE AS juris_data_julgamento,
    principal.orgao          AS juris_orgao,
    principal.relator        AS juris_relator,
    principal.classe_judicial AS juris_classe,
    principal.url_portal     AS juris_url
FROM agg
JOIN principal USING (nr_processo)
"""

_STJ_AGG_SQL = """
SELECT
    regexp_replace("numeroProcesso", '[^0-9]', '', 'g') AS nr_processo,
    FIRST(id ORDER BY "dataDecisao" DESC NULLS LAST)::VARCHAR AS stj_id,
    FIRST("siglaClasse" ORDER BY "dataDecisao" DESC NULLS LAST) AS stj_classe,
    FIRST("ministroRelator" ORDER BY "dataDecisao" DESC NULLS LAST) AS stj_relator,
    FIRST("tema" ORDER BY "dataDecisao" DESC NULLS LAST)::VARCHAR AS stj_tema,
    FIRST("teseJuridica" ORDER BY "dataDecisao" DESC NULLS LAST) AS stj_tese,
    FIRST("ementa" ORDER BY "dataDecisao" DESC NULLS LAST) AS stj_ementa,
    MAX("dataDecisao")::DATE AS stj_data_decisao,
    MAX("dataPublicacao")::DATE AS stj_data_publicacao
FROM acordaos
WHERE length(regexp_replace("numeroProcesso", '[^0-9]', '', 'g')) = 20
GROUP BY nr_processo
"""

# DataJud capa is a per-(numero, grau, orgao) table; collapse to one row per
# CNJ preferring the most recently updated document (usually the highest grau
# reached). data_ajuizamento takes the earliest — the original filing.
_DATAJUD_AGG_SQL = """
SELECT
    numero_processo AS nr_processo,
    FIRST(classe_nome ORDER BY ultima_atualizacao DESC NULLS LAST) AS classe_oficial,
    FIRST(assuntos ORDER BY ultima_atualizacao DESC NULLS LAST) AS assuntos,
    FIRST(orgao_julgador ORDER BY ultima_atualizacao DESC NULLS LAST) AS orgao_julgador,
    FIRST(grau ORDER BY ultima_atualizacao DESC NULLS LAST) AS grau,
    MIN(data_ajuizamento) AS data_ajuizamento,
    MAX(ultima_atualizacao) AS ultima_atualizacao
FROM datajud_capa
WHERE length(regexp_replace(numero_processo, '[^0-9]', '', 'g')) = 20
GROUP BY numero_processo
"""

_UNIFICADOS_SQL = """
WITH
    base AS (
        SELECT
            COALESCE(d.nr_processo, j.nr_processo, s.nr_processo, dj.nr_processo) AS nr_processo,
            d.djen_primeira_pub,
            d.djen_ultima_pub,
            d.djen_n_publicacoes,
            d.djen_tribunais,
            j.juris_n_documentos,
            j.juris_tipos,
            j.juris_data_julgamento,
            j.juris_orgao,
            j.juris_relator,
            j.juris_classe,
            j.juris_url,
            s.stj_id,
            s.stj_classe,
            s.stj_relator,
            s.stj_tema,
            s.stj_tese,
            s.stj_ementa,
            s.stj_data_decisao,
            s.stj_data_publicacao,
            -- DataJud enrichment (RFC 0010) — NULL/false when the capa is absent
            dj.classe_oficial,
            dj.assuntos,
            dj.orgao_julgador,
            dj.grau,
            dj.data_ajuizamento,
            dj.ultima_atualizacao,
            (dj.nr_processo IS NOT NULL) AS tem_datajud,
            (CASE WHEN d.nr_processo IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN j.nr_processo IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN s.nr_processo IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN dj.nr_processo IS NOT NULL THEN 1 ELSE 0 END)::INTEGER AS n_fontes,
            list_filter(
                ['djen', 'juris', 'stj', 'datajud'],
                x -> (
                    (x = 'djen'    AND d.nr_processo IS NOT NULL) OR
                    (x = 'juris'   AND j.nr_processo IS NOT NULL) OR
                    (x = 'stj'     AND s.nr_processo IS NOT NULL) OR
                    (x = 'datajud' AND dj.nr_processo IS NOT NULL)
                )
            ) AS fontes,
            NOW() AS updated_at
        FROM djen_agg d
        FULL OUTER JOIN juris_agg   j USING (nr_processo)
        FULL OUTER JOIN stj_agg     s USING (nr_processo)
        FULL OUTER JOIN datajud_agg dj USING (nr_processo)
    )
SELECT
    base.nr_processo,
    -- Build display mask inline (20 digits → NNNNNNN-DD.AAAA.J.TR.OOOO)
    (base.nr_processo[1:7] || '-' || base.nr_processo[8:9] || '.' ||
     base.nr_processo[10:13] || '.' || base.nr_processo[14:14] || '.' ||
     base.nr_processo[15:16] || '.' || base.nr_processo[17:20]) AS nr_processo_mascara,
    djen_primeira_pub,
    djen_ultima_pub,
    djen_n_publicacoes,
    djen_tribunais,
    juris_n_documentos,
    juris_tipos,
    juris_data_julgamento,
    juris_orgao,
    juris_relator,
    juris_classe,
    juris_url,
    stj_id,
    stj_classe,
    stj_relator,
    stj_tema,
    stj_tese,
    stj_ementa,
    stj_data_decisao,
    stj_data_publicacao,
    classe_oficial,
    assuntos,
    orgao_julgador,
    grau,
    data_ajuizamento,
    ultima_atualizacao,
    tem_datajud,
    fontes,
    n_fontes,
    updated_at
FROM base
ORDER BY base.nr_processo
"""

_DOCUMENTOS_SQL = """
-- JURIS documents
SELECT
    regexp_replace(nr_processo, '[^0-9]', '', 'g') AS nr_processo,
    'juris'          AS fonte,
    id_documento::VARCHAR AS id_documento,
    tipo,
    data_julgamento::DATE AS data,
    url_portal       AS url,
    left(texto_limpo, 500) AS resumo
FROM tjro_juris
WHERE length(regexp_replace(nr_processo, '[^0-9]', '', 'g')) = 20

UNION ALL

-- STJ documents
SELECT
    regexp_replace("numeroProcesso", '[^0-9]', '', 'g') AS nr_processo,
    'stj'            AS fonte,
    id::VARCHAR      AS id_documento,
    "siglaClasse"    AS tipo,
    "dataDecisao"::DATE AS data,
    ''               AS url,
    left("ementa", 500) AS resumo
FROM acordaos
WHERE length(regexp_replace("numeroProcesso", '[^0-9]', '', 'g')) = 20

ORDER BY nr_processo, data DESC NULLS LAST
"""


# ── View registry ──────────────────────────────────────────────────────────────
# Single source of truth for the data sources available to .qmd SQL, in BOTH
# modes: `register` wires the real data for rendering; `synthetic` creates an
# empty relation with the same columns for --check (no network, no files).


@dataclass(frozen=True)
class ViewSpec:
    """A named SQL data source: real registration + synthetic schema for --check."""

    name: str
    register: Callable[[duckdb.DuckDBPyConnection], bool]
    synthetic: Callable[[duckdb.DuckDBPyConnection], None]


def _register_view_from_parquet(con: duckdb.DuckDBPyConnection, name: str, path: Path) -> None:
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")


def _register_manifest(con: duckdb.DuckDBPyConnection) -> bool:
    path = _try_download_parquet(MANIFEST_PARQUET_URL, LOCAL_MANIFEST_PARQUET, "manifest")
    if path is None:
        return False
    _register_view_from_parquet(con, "manifest", path)
    return True


def _register_local_parquet(con: duckdb.DuckDBPyConnection, name: str, path: Path) -> bool:
    if not path.exists():
        return False
    print(f"Using local {name}: {path}")
    _register_view_from_parquet(con, name, path)
    return True


def _register_lawyer_ratings(con: duckdb.DuckDBPyConnection) -> bool:
    return _register_local_parquet(
        con, "lawyer_ratings", DEV_RATINGS_DIR / "lawyer_ratings.parquet"
    )


def _register_ratings_history(con: duckdb.DuckDBPyConnection) -> bool:
    return _register_local_parquet(
        con, "ratings_history", DEV_RATINGS_DIR / "ratings_history.parquet"
    )


def _register_acordaos(con: duckdb.DuckDBPyConnection) -> bool:
    stj_parquet = _try_download_parquet(_STJ_PARQUET_IA_URL, _STJ_PARQUET, "STJ parquet")
    if stj_parquet is None:
        return False
    # qmd files query "FROM acordaos" — register under that name
    _register_view_from_parquet(con, "acordaos", stj_parquet)
    return True


def _register_comunicacoes(con: duckdb.DuckDBPyConnection) -> bool:
    """DJEN comunicacoes, discovered via indice_processual.parquet's own arquivo_ia_url.

    RFC 0014 M2: rather than re-deriving which comunicacoes.parquet files
    exist (a second, independent lookup against the causaganha-catalog
    manifest, duplicating scripts/reconcile_processos.py's own discovery),
    reuse the index's own djen rows — it already recorded exactly which
    per-date IA item each DJEN record came from.
    """
    indice_path = _try_download_parquet(
        _INDICE_PROCESSUAL_IA_URL, _INDICE_PROCESSUAL_PARQUET, "indice_processual"
    )
    if indice_path is None:
        return False
    urls = [
        row[0]
        for row in con.execute(
            f"SELECT DISTINCT arquivo_ia_url FROM read_parquet('{indice_path}') "
            "WHERE fonte = 'djen'"
        ).fetchall()
    ]
    if not urls:
        return False
    url_list = ", ".join(f"'{u}'" for u in urls)
    print(f"Registering DJEN comunicacoes view: {len(urls)} parquet file(s) via indice_processual")
    con.execute(
        f"CREATE VIEW comunicacoes AS SELECT * FROM read_parquet([{url_list}], union_by_name=true)"
    )
    return True


def _ensure_view(con: duckdb.DuckDBPyConnection, name: str, synthetic: Callable) -> None:
    """Guarantee *name* exists on *con*, falling back to its empty synthetic schema.

    Used by the aggregate views below: their SQL (moved from
    scripts/reconcile_processos.py) references comunicacoes/tjro_juris/
    acordaos/datajud_capa unconditionally, so every one of those must exist
    (even if empty) regardless of whether that source's own registration
    succeeded for this run — an unavailable source is a legitimate, common
    case (RFC 0007), not a failure of the aggregate.
    """
    try:
        con.execute(f"SELECT 1 FROM {name} LIMIT 0")
    except duckdb.Error:
        synthetic(con)


def _register_processos_unificados(con: duckdb.DuckDBPyConnection) -> bool:
    """Reconstruct the processos_unificados VIEW by aggregating the raw sources.

    VIEW_SPECS registers acordaos/tjro_juris/datajud_capa (and this
    function registers comunicacoes) before this runs, so _ensure_view's
    fallback only fires for a source that genuinely didn't load this run —
    the aggregate always succeeds, possibly with NULLs for a missing source,
    exactly like scripts/reconcile_processos.py's own FULL OUTER JOIN did.
    """
    _register_comunicacoes(con)
    for name, synth in (
        ("comunicacoes", _synthetic_comunicacoes),
        ("tjro_juris", _synthetic_tjro_juris),
        ("acordaos", _synthetic_acordaos),
        ("datajud_capa", _synthetic_datajud_capa),
    ):
        _ensure_view(con, name, synth)
    con.execute(f"CREATE OR REPLACE TEMP VIEW djen_agg AS {_DJEN_AGG_SQL}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW juris_agg AS {_JURIS_AGG_SQL}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW stj_agg AS {_STJ_AGG_SQL}")
    con.execute(f"CREATE OR REPLACE TEMP VIEW datajud_agg AS {_DATAJUD_AGG_SQL}")
    con.execute(f"CREATE VIEW processos_unificados AS {_UNIFICADOS_SQL}")
    return True


def _register_processo_documentos(con: duckdb.DuckDBPyConnection) -> bool:
    """Reconstruct the processo_documentos VIEW (JURIS + STJ) from raw sources."""
    for name, synth in (
        ("tjro_juris", _synthetic_tjro_juris),
        ("acordaos", _synthetic_acordaos),
    ):
        _ensure_view(con, name, synth)
    con.execute(f"CREATE VIEW processo_documentos AS {_DOCUMENTOS_SQL}")
    return True


def _register_datajud_capa(con: duckdb.DuckDBPyConnection) -> bool:
    # datajud enrich writes: data/datajud/datajud-capa-{tribunal}.parquet
    datajud_files = sorted(ROOT.glob("data/datajud/datajud-capa-*.parquet"))
    if not datajud_files:
        return False
    datajud_list = ", ".join(f"'{p}'" for p in datajud_files)
    print(f"Using local DataJud capa parquets: {len(datajud_files)} files")
    con.execute(f"CREATE VIEW datajud_capa AS SELECT * FROM read_parquet([{datajud_list}])")
    return True


def _register_tjro_juris(con: duckdb.DuckDBPyConnection) -> bool:
    # Consolidate command writes: data/tjro_juris/<year>/tjro-juris-<year>.parquet
    juris_files = sorted(ROOT.glob("data/tjro_juris/*/tjro-juris-*.parquet"))
    if not juris_files:
        return False
    juris_list = ", ".join(f"'{p}'" for p in juris_files)
    print(f"Using local JURIS parquets: {len(juris_files)} files")
    con.execute(f"CREATE VIEW tjro_juris AS SELECT * FROM read_parquet([{juris_list}])")
    return True


# ── Synthetic schemas (for --check) ────────────────────────────────────────────


def _synthetic_manifest(con: duckdb.DuckDBPyConnection) -> None:
    """Empty manifest with columns from djen_backup.manifest.HEADER (the CSV writer).

    Types mirror what read_csv_auto infers on the real CSV.
    """
    type_overrides = {"date": "DATE", "updated_at": "TIMESTAMP"}
    cols = ", ".join(
        f"{col} {type_overrides.get(col, 'VARCHAR')}" for col in _MANIFEST_HEADER.split(",")
    )
    con.execute(f"CREATE TABLE manifest ({cols})")


def _synthetic_catalog_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    """Empty `table` with the schema from storage/schema.sql.

    That DDL defines the catalog tables that export_ratings.py copies verbatim
    to the parquets consumed here — same definition, not a hand copy.
    """
    scratch = duckdb.connect()
    try:
        scratch.execute(_CATALOG_SCHEMA_SQL.read_text(encoding="utf-8"))
        empty = scratch.execute(f"SELECT * FROM {table} LIMIT 0").arrow()
    finally:
        scratch.close()
    con.register(table, empty)


def _synthetic_lawyer_ratings(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_catalog_table(con, "lawyer_ratings")


def _synthetic_ratings_history(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_catalog_table(con, "ratings_history")


# The STJ parquet schema is auto-detected from the portal's JSON by
# stj_acordaos.dedup (no static schema exists in-repo), so this is the single
# in-repo definition of the columns the .qmd contracts and reconcile SQL use.
_ACORDAOS_SYNTHETIC_COLUMNS: dict[str, str] = {
    "id": "VARCHAR",
    "numeroProcesso": "VARCHAR",
    "siglaClasse": "VARCHAR",
    "ministroRelator": "VARCHAR",
    "tema": "VARCHAR",
    "teseJuridica": "VARCHAR",
    "ementa": "VARCHAR",
    "dataDecisao": "DATE",
    "dataPublicacao": "DATE",
}


def _synthetic_acordaos(con: duckdb.DuckDBPyConnection) -> None:
    cols = ", ".join(f'"{col}" {typ}' for col, typ in _ACORDAOS_SYNTHETIC_COLUMNS.items())
    con.execute(f"CREATE TABLE acordaos ({cols})")


def _synthetic_tjro_juris(con: duckdb.DuckDBPyConnection) -> None:
    """Empty tjro_juris from the producer's own parquet schema (tjro_juris CLI)."""
    con.register("tjro_juris", _TJRO_JURIS_SCHEMA.empty_table())


def _synthetic_datajud_capa(con: duckdb.DuckDBPyConnection) -> None:
    """Empty datajud_capa from the producer's own parquet schema (datajud CLI)."""
    con.register("datajud_capa", _DATAJUD_CAPA_SCHEMA.empty_table())


def _synthetic_comunicacoes(con: duckdb.DuckDBPyConnection) -> None:
    """Empty comunicacoes — the columns _DJEN_AGG_SQL needs (not the full DJEN schema)."""
    con.execute(
        "CREATE TABLE comunicacoes "
        "(numero_processo VARCHAR, data_disponibilizacao DATE, tribunal VARCHAR)"
    )


def _reconcile_sources_connection() -> duckdb.DuckDBPyConnection:
    """Scratch connection with empty inputs + aggregation views for the moved reconcile SQL.

    The processos_unificados/processo_documentos schemas are derived by
    running this file's own aggregation SQL (moved from
    scripts/reconcile_processos.py — see the constants above) over empty
    sources, so --check can never drift from what render_all actually
    computes.
    """
    scratch = duckdb.connect()
    _synthetic_comunicacoes(scratch)
    _synthetic_tjro_juris(scratch)
    _synthetic_acordaos(scratch)
    _synthetic_datajud_capa(scratch)
    scratch.execute(f"CREATE VIEW djen_agg AS {_DJEN_AGG_SQL}")
    scratch.execute(f"CREATE VIEW juris_agg AS {_JURIS_AGG_SQL}")
    scratch.execute(f"CREATE VIEW stj_agg AS {_STJ_AGG_SQL}")
    scratch.execute(f"CREATE VIEW datajud_agg AS {_DATAJUD_AGG_SQL}")
    return scratch


def _synthetic_from_reconcile_sql(con: duckdb.DuckDBPyConnection, name: str, sql: str) -> None:
    scratch = _reconcile_sources_connection()
    try:
        empty = scratch.execute(f"SELECT * FROM ({sql}) LIMIT 0").arrow()
    finally:
        scratch.close()
    con.register(name, empty)


def _synthetic_processos_unificados(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_from_reconcile_sql(con, "processos_unificados", _UNIFICADOS_SQL)


def _synthetic_processo_documentos(con: duckdb.DuckDBPyConnection) -> None:
    _synthetic_from_reconcile_sql(con, "processo_documentos", _DOCUMENTOS_SQL)


# acordaos/tjro_juris/datajud_capa MUST come before processos_unificados/
# processo_documentos: those two build synthetic empty fallbacks for any
# source not already registered (_ensure_view), which would collide with a
# later CREATE VIEW from this same source's own spec if the order were
# reversed. comunicacoes has no standalone spec — no .qmd queries it
# directly, only _register_processos_unificados does (via
# _register_comunicacoes internally).
VIEW_SPECS: tuple[ViewSpec, ...] = (
    ViewSpec("manifest", _register_manifest, _synthetic_manifest),
    ViewSpec("lawyer_ratings", _register_lawyer_ratings, _synthetic_lawyer_ratings),
    ViewSpec("ratings_history", _register_ratings_history, _synthetic_ratings_history),
    ViewSpec("acordaos", _register_acordaos, _synthetic_acordaos),
    ViewSpec("tjro_juris", _register_tjro_juris, _synthetic_tjro_juris),
    ViewSpec("datajud_capa", _register_datajud_capa, _synthetic_datajud_capa),
    ViewSpec(
        "processos_unificados", _register_processos_unificados, _synthetic_processos_unificados
    ),
    ViewSpec("processo_documentos", _register_processo_documentos, _synthetic_processo_documentos),
)


# ── Execution ──────────────────────────────────────────────────────────────────


def run_query(con: duckdb.DuckDBPyConnection, sql: str, fmt: str) -> object:
    """Execute SQL and return serializable data in the requested format."""
    rows = con.execute(sql).fetchall()
    columns = [d[0] for d in con.description]

    if fmt == "object":
        if len(rows) != 1:
            msg = f"format=object expects 1 row, got {len(rows)}"
            raise ValueError(msg)
        return dict(zip(columns, rows[0], strict=False))

    # default: array of row dicts
    return [dict(zip(columns, row, strict=False)) for row in rows]


def json_default(obj: object) -> str:
    """Serialize non-JSON types (date, datetime) as ISO strings."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    msg = f"Object of type {type(obj).__name__} is not JSON serializable"
    raise TypeError(msg)


def _first_line(exc: duckdb.Error) -> str:
    return str(exc).splitlines()[0] if str(exc) else type(exc).__name__


def check_queries(queries_dir: Path | None = None) -> list[str]:
    """Statically validate all .qmd contracts (frontmatter + SQL). No network.

    SQL is executed against empty synthetic relations built from the same
    VIEW_SPECS registry the render uses, catching syntax errors, unknown
    columns and references to unregistered views. Returns the list of
    failures (empty = all contracts valid).
    """
    queries_dir = QUERIES_DIR if queries_dir is None else queries_dir
    qmds = sorted(queries_dir.glob("*.qmd"))
    if not qmds:
        return [f"no .qmd files found in {queries_dir}"]

    con = duckdb.connect()
    for spec in VIEW_SPECS:
        spec.synthetic(con)

    failures: list[str] = []
    for qmd in qmds:
        errors: list[str] = []
        try:
            frontmatter, sql = parse_qmd(qmd)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            errors.extend(validate_frontmatter(frontmatter))
            try:
                con.execute(sql)
            except duckdb.Error as exc:
                errors.append(f"SQL error: {_first_line(exc)}")

        if errors:
            print(f"FAIL {qmd.name}")
            for error in errors:
                print(f"     - {error}")
            failures.extend(f"{qmd.name}: {error}" for error in errors)
        else:
            print(f"OK   {qmd.name}")

    return failures


def render_all(
    queries_dir: Path | None = None,
    public_dir: Path | None = None,
    specs: tuple[ViewSpec, ...] | None = None,
) -> tuple[int, list[str]]:
    """Render all .qmd files. Returns (rendered_count, failures).

    A failure is a contract that should have produced JSON but could not:
    invalid frontmatter, or a missing data source for a non-``optional``
    contract. Optional contracts with missing sources emit a named warning
    and are not failures. The caller decides whether failures are fatal
    (--strict) or merely reported.
    """
    queries_dir = QUERIES_DIR if queries_dir is None else queries_dir
    public_dir = PUBLIC_DIR if public_dir is None else public_dir
    specs = VIEW_SPECS if specs is None else specs
    qmds = sorted(queries_dir.glob("*.qmd"))
    if not qmds:
        print(f"No .qmd files in {queries_dir}", file=sys.stderr)
        return 0, []

    con = duckdb.connect()
    for spec in specs:
        spec.register(con)

    count = 0
    failures: list[str] = []
    for qmd in qmds:
        print(f"\n→ {qmd.name}")
        try:
            frontmatter, sql = parse_qmd(qmd)
        except ValueError as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            failures.append(f"{qmd.name}: {exc}")
            continue

        fm_errors = validate_frontmatter(frontmatter)
        if fm_errors:
            print(f"  ERROR: invalid frontmatter — {'; '.join(fm_errors)}", file=sys.stderr)
            failures.append(f"{qmd.name}: {'; '.join(fm_errors)}")
            continue

        output = frontmatter["output"]
        fmt = frontmatter["format"]
        optional = frontmatter.get("optional", False)

        try:
            data = run_query(con, sql, fmt)
        except duckdb.CatalogException as exc:
            reason = _first_line(exc)
            if optional:
                print(
                    f"  WARNING: optional contract skipped — {reason}; {output} not generated",
                    file=sys.stderr,
                )
            else:
                print(f"  ERROR: required contract failed — {reason}", file=sys.stderr)
                failures.append(f"{qmd.name}: missing required data source — {reason}")
            continue

        output_path = public_dir / output.lstrip("/")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(data, indent=2, default=json_default),
            encoding="utf-8",
        )
        print(f"  → {output_path} ({output_path.stat().st_size:,} bytes)")
        count += 1

    return count, failures


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(description="Render .qmd query contracts to JSON.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate frontmatter and SQL against synthetic schemas (no network, "
        "no files written); exit 1 listing every invalid .qmd",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if any required (non-optional) contract fails to render",
    )
    args = parser.parse_args(argv)

    if args.check:
        failures = check_queries()
        if failures:
            print(f"\n--check failed: {len(failures)} problem(s):", file=sys.stderr)
            for failure in failures:
                print(f"  - {failure}", file=sys.stderr)
            return 1
        print("\n--check passed: all query contracts are valid.")
        return 0

    count, failures = render_all()
    print(f"\n{count} queries rendered.")
    if failures:
        print(f"{len(failures)} contract(s) failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
