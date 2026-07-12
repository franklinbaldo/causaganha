#!/usr/bin/env python3
"""Reconcile DJEN x TJRO JURIS x STJ into processos_unificados.

Pipeline:
  1. Load DJEN from every consolidated comunicacoes.parquet (discovered via the
     causaganha-catalog manifest) — GROUP BY nr_processo
  2. Load JURIS from tjro-juris-<year>.parquet files — GROUP BY nr_processo
  3. Load STJ from stj-acordaos.parquet — filter to CNJ numbers only
  4. Full outer join the three aggregations in DuckDB
  5. Optional DataJud enrichment (RFC 0010): LEFT JOIN the official capa
     (classe_oficial, assuntos, orgao_julgador, grau, data_ajuizamento,
     ultima_atualizacao, tem_datajud) when datajud-capa-*.parquet exists —
     without it the columns are NULL/false and behaviour is unchanged
  6. Write processos_unificados.parquet + processo_documentos.parquet
  7. Upload both to IA item causaganha-dashboard
"""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import duckdb

from datajud.archive import CAPA_SCHEMA as _DATAJUD_CAPA_SCHEMA


ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

_PARQUET_UNIFICADOS = DATA_DIR / "processos_unificados.parquet"
_PARQUET_DOCUMENTOS = DATA_DIR / "processo_documentos.parquet"

_IA_BASE = "https://archive.org/download"
_IA_ITEM_DASHBOARD = "causaganha-dashboard"
_IA_CATALOG_MANIFEST_URL = f"{_IA_BASE}/causaganha-catalog/manifest.parquet"

_STJ_PARQUET = DATA_DIR / "stj" / "stj-acordaos.parquet"
_STJ_IA_URL = f"{_IA_BASE}/stj-acordaos-primeira-secao/stj-acordaos.parquet"

# DataJud capa parquets (datajud enrich CLI, RFC 0010) — optional enrichment.
_DATAJUD_DIR = DATA_DIR / "datajud"


# ── CNJ normalisation ──────────────────────────────────────────────────────────


def normalizar_cnj(n: str | None) -> str:
    """Remove non-digits; return 20-digit string or '' if invalid."""
    d = re.sub(r"\D", "", n or "")
    return d if len(d) == 20 else ""


def formatar_cnj(n: str) -> str:
    """20 digits → NNNNNNN-DD.AAAA.J.TR.OOOO."""
    if len(n) != 20:
        return n
    return f"{n[0:7]}-{n[7:9]}.{n[9:13]}.{n[13:14]}.{n[14:16]}.{n[16:20]}"


# ── Data acquisition ───────────────────────────────────────────────────────────


def _download(url: str, dest: Path, label: str) -> Path:
    print(f"Downloading {label} from {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as resp:
        dest.write_bytes(resp.read())
    print(f"  saved to {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def comunicacoes_parquet_urls(con: duckdb.DuckDBPyConnection) -> list[str]:
    """URLs of every consolidated comunicacoes.parquet, from the IA catalog.

    consolidate-parquet.yml uploads one comunicacoes.parquet per consolidated
    date (item djen-YYYY-MM-DD); causaganha-catalog/manifest.parquet is the
    index of every such file across every item, kept fresh by
    update-catalog.yml. Querying it (instead of e.g. listing IA items
    directly) keeps this in sync with whatever has actually been consolidated
    without hand-enumerating dates.
    """
    try:
        rows = con.execute(
            "SELECT DISTINCT ia_url FROM read_parquet(?) WHERE table_name = 'comunicacoes'",
            [_IA_CATALOG_MANIFEST_URL],
        ).fetchall()
    except duckdb.Error as exc:
        print(f"  WARNING: could not read IA catalog manifest — {exc}", file=sys.stderr)
        return []
    return sorted(r[0] for r in rows)


def ensure_stj_parquet() -> Path | None:
    if _STJ_PARQUET.exists():
        print(f"Using local STJ parquet: {_STJ_PARQUET}")
        return _STJ_PARQUET
    try:
        return _download(_STJ_IA_URL, _STJ_PARQUET, "STJ parquet")
    except OSError as exc:
        print(f"  WARNING: could not download STJ parquet — {exc}", file=sys.stderr)
        return None


def juris_parquet_files() -> list[Path]:
    return sorted(ROOT.glob("data/tjro_juris/*/tjro-juris-*.parquet"))


def datajud_parquet_files() -> list[Path]:
    return sorted(_DATAJUD_DIR.glob("datajud-capa-*.parquet"))


# ── IA upload ──────────────────────────────────────────────────────────────────


def upload_to_ia(path: Path, remote_name: str) -> None:
    """PUT a file to the causaganha-dashboard IA item via httpx."""
    import httpx

    ia_key = _ia_credentials()
    if not ia_key:
        print(f"  SKIP upload (no IA credentials): {remote_name}", file=sys.stderr)
        return

    url = f"https://s3.us.archive.org/{_IA_ITEM_DASHBOARD}/{remote_name}"
    headers = {
        "Authorization": f"LOW {ia_key}",
        "x-archive-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "x-archive-meta-subject": "causaganha;reconciliacao;processos",
    }
    data = path.read_bytes()
    print(f"  Uploading {remote_name} ({len(data):,} bytes) → IA")
    with httpx.Client(timeout=300) as client:
        resp = client.put(url, content=data, headers=headers)
        resp.raise_for_status()
    print(f"  uploaded {remote_name}")


def _ia_credentials() -> str | None:
    import os

    access = os.environ.get("IA_ACCESS_KEY", "")
    secret = os.environ.get("IA_SECRET_KEY", "")
    if access and secret:
        return f"{access}:{secret}"
    return None


# ── Aggregation SQL ────────────────────────────────────────────────────────────

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


# ── Main pipeline ──────────────────────────────────────────────────────────────


def reconcile(*, upload: bool = True) -> dict[str, Any]:
    stj_path = ensure_stj_parquet()
    juris_files = juris_parquet_files()

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")

    # Register DJEN comunicacoes view (union of every consolidated date, read
    # straight off IA — there's no single local cache file for this, unlike
    # STJ/JURIS, since it's one small parquet per consolidated date).
    comunicacoes_urls = comunicacoes_parquet_urls(con)
    if comunicacoes_urls:
        url_list = ", ".join(f"'{u}'" for u in comunicacoes_urls)
        print(f"Registering DJEN comunicacoes view: {len(comunicacoes_urls)} parquet file(s)")
        con.execute(
            f"CREATE VIEW comunicacoes AS SELECT * FROM read_parquet([{url_list}], "
            "union_by_name=true)"
        )
    else:
        print(
            "WARNING: no comunicacoes.parquet in the IA catalog — DJEN contribution will be empty",
            file=sys.stderr,
        )
        con.execute(
            "CREATE VIEW comunicacoes AS "
            "SELECT NULL::VARCHAR AS numero_processo, NULL::DATE AS data_disponibilizacao, "
            "NULL::VARCHAR AS tribunal WHERE FALSE"
        )

    # Register JURIS view (union of consolidated yearly parquets)
    if juris_files:
        juris_list = ", ".join(f"'{p}'" for p in juris_files)
        print(f"Registering JURIS view: {len(juris_files)} parquet file(s)")
        con.execute(f"CREATE VIEW tjro_juris AS SELECT * FROM read_parquet([{juris_list}])")
    else:
        print(
            "WARNING: no JURIS parquets found — JURIS contribution will be empty",
            file=sys.stderr,
        )
        con.execute(
            "CREATE VIEW tjro_juris AS "
            "SELECT NULL::VARCHAR AS nr_processo, NULL::INTEGER AS id_documento, "
            "NULL::VARCHAR AS tipo, NULL::DATE AS data_julgamento, "
            "NULL::VARCHAR AS orgao, NULL::VARCHAR AS relator, "
            "NULL::VARCHAR AS classe_judicial, NULL::VARCHAR AS url_portal, "
            "NULL::VARCHAR AS texto_limpo "
            "WHERE FALSE"
        )

    # Register STJ view
    if stj_path is not None:
        print(f"Registering STJ view: {stj_path}")
        con.execute(f"CREATE VIEW acordaos AS SELECT * FROM read_parquet('{stj_path}')")
    else:
        print("WARNING: STJ parquet unavailable — STJ contribution will be empty", file=sys.stderr)
        con.execute(
            "CREATE VIEW acordaos AS "
            'SELECT NULL::VARCHAR AS "numeroProcesso", NULL::VARCHAR AS id, '
            'NULL::VARCHAR AS "siglaClasse", NULL::VARCHAR AS "ministroRelator", '
            'NULL::VARCHAR AS "tema", NULL::VARCHAR AS "teseJuridica", '
            'NULL::VARCHAR AS "ementa", NULL::DATE AS "dataDecisao", '
            'NULL::DATE AS "dataPublicacao" '
            "WHERE FALSE"
        )

    # Build aggregation CTEs
    print("Building DJEN aggregation…")
    con.execute(f"CREATE TEMP TABLE djen_agg AS {_DJEN_AGG_SQL}")
    djen_count = con.execute("SELECT COUNT(*) FROM djen_agg").fetchone()[0]
    print(f"  {djen_count:,} DJEN processes")

    print("Building JURIS aggregation…")
    con.execute(f"CREATE TEMP TABLE juris_agg AS {_JURIS_AGG_SQL}")
    juris_count = con.execute("SELECT COUNT(*) FROM juris_agg").fetchone()[0]
    print(f"  {juris_count:,} JURIS processes")

    print("Building STJ aggregation…")
    con.execute(f"CREATE TEMP TABLE stj_agg AS {_STJ_AGG_SQL}")
    stj_count = con.execute("SELECT COUNT(*) FROM stj_agg").fetchone()[0]
    print(f"  {stj_count:,} STJ processes (with valid CNJ number)")

    # DataJud capa (optional enrichment) — join only when the parquet exists
    # AND has the columns _DATAJUD_AGG_SQL needs; without it the datajud
    # columns are NULL and tem_datajud is false. The empty fallback is
    # derived from the producer's own pyarrow schema (datajud.archive.
    # CAPA_SCHEMA) rather than hand-typed, so it can't drift from it — same
    # pattern as scripts/render_queries.py's _synthetic_datajud_capa.
    print("Building DataJud aggregation…")
    _datajud_required_cols = {
        "numero_processo",
        "classe_nome",
        "assuntos",
        "orgao_julgador",
        "grau",
        "data_ajuizamento",
        "ultima_atualizacao",
    }
    datajud_files = datajud_parquet_files()
    if datajud_files:
        datajud_list = ", ".join(f"'{p}'" for p in datajud_files)
        print(f"  Registering DataJud capa view: {len(datajud_files)} parquet file(s)")
        con.execute(f"CREATE VIEW datajud_capa AS SELECT * FROM read_parquet([{datajud_list}])")
        datajud_cols = {row[0] for row in con.execute("DESCRIBE datajud_capa").fetchall()}
        if not _datajud_required_cols <= datajud_cols:
            missing = sorted(_datajud_required_cols - datajud_cols)
            print(
                f"  SKIP: datajud-capa-*.parquet missing column(s) {missing} — "
                "DataJud enrichment will be empty (incompatible/partial parquet?)",
                file=sys.stderr,
            )
            con.execute("DROP VIEW datajud_capa")
            con.register("datajud_capa", _DATAJUD_CAPA_SCHEMA.empty_table())
    else:
        print(
            "  SKIP: no datajud-capa-*.parquet found — DataJud enrichment will be empty",
            file=sys.stderr,
        )
        con.register("datajud_capa", _DATAJUD_CAPA_SCHEMA.empty_table())
    con.execute(f"CREATE TEMP TABLE datajud_agg AS {_DATAJUD_AGG_SQL}")
    datajud_count = con.execute("SELECT COUNT(*) FROM datajud_agg").fetchone()[0]
    print(f"  {datajud_count:,} DataJud processes")

    # Full outer join → processos_unificados
    print("Running full outer join…")
    con.execute(f"CREATE TEMP TABLE processos_unificados AS {_UNIFICADOS_SQL}")
    total = con.execute("SELECT COUNT(*) FROM processos_unificados").fetchone()[0]
    multi = con.execute("SELECT COUNT(*) FROM processos_unificados WHERE n_fontes >= 2").fetchone()[
        0
    ]
    print(f"  {total:,} unified processes ({multi:,} present in 2+ sources)")

    # Write processos_unificados.parquet
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing {_PARQUET_UNIFICADOS}")
    con.execute(
        f"COPY processos_unificados TO '{_PARQUET_UNIFICADOS}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )

    # Build processo_documentos (JURIS + STJ only — DJEN's per-process rollup
    # already lives in processos_unificados via djen_agg; adding individual
    # DJEN communications here would need a join through textos for a resumo)
    print("Writing processo_documentos.parquet…")
    con.execute(
        f"COPY ({_DOCUMENTOS_SQL}) TO '{_PARQUET_DOCUMENTOS}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    doc_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{_PARQUET_DOCUMENTOS}')"
    ).fetchone()[0]
    print(f"  {doc_count:,} document rows")

    if upload:
        upload_to_ia(_PARQUET_UNIFICADOS, "processos_unificados.parquet")
        if _PARQUET_DOCUMENTOS.exists():
            upload_to_ia(_PARQUET_DOCUMENTOS, "processo_documentos.parquet")

    return {
        "djen": djen_count,
        "juris": juris_count,
        "stj": stj_count,
        "datajud": datajud_count,
        "total": total,
        "multi_fonte": multi,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reconcile DJEN x JURIS x STJ processos")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading to Internet Archive",
    )
    args = parser.parse_args()

    stats = reconcile(upload=not args.no_upload)  # type: ignore[call-arg]
    total = stats["total"]
    multi = stats["multi_fonte"]
    print(f"\nDone. {total:,} processos_unificados ({multi:,} multi-fonte).")
