#!/usr/bin/env python3
"""Reconcile DJEN x TJRO JURIS x STJ into processos_unificados.

Pipeline:
  1. Load DJEN from sync-manifest parquet — GROUP BY nr_processo
  2. Load JURIS from tjro-juris-<year>.parquet files — GROUP BY nr_processo
  3. Load STJ from stj-acordaos.parquet — filter to CNJ numbers only
  4. Full outer join the three aggregations in DuckDB
  5. Write processos_unificados.parquet + processo_documentos.parquet
  6. Upload both to IA item causaganha-dashboard
"""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

import duckdb


ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

_PARQUET_UNIFICADOS = DATA_DIR / "processos_unificados.parquet"
_PARQUET_DOCUMENTOS = DATA_DIR / "processo_documentos.parquet"

_IA_BASE = "https://archive.org/download"
_IA_ITEM_DASHBOARD = "causaganha-dashboard"
_IA_MANIFEST_CSV_URL = f"{_IA_BASE}/{_IA_ITEM_DASHBOARD}/sync-manifest.csv"
_LOCAL_MANIFEST = DATA_DIR / "sync-manifest.csv"

_STJ_PARQUET = DATA_DIR / "stj" / "stj-acordaos.parquet"
_STJ_IA_URL = f"{_IA_BASE}/stj-acordaos-primeira-secao/stj-acordaos.parquet"


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


def ensure_manifest() -> Path:
    if _LOCAL_MANIFEST.exists():
        print(f"Using local manifest: {_LOCAL_MANIFEST}")
        return _LOCAL_MANIFEST
    return _download(_IA_MANIFEST_CSV_URL, _LOCAL_MANIFEST, "sync-manifest.csv")


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
    MIN(data_publicacao)::DATE  AS djen_primeira_pub,
    MAX(data_publicacao)::DATE  AS djen_ultima_pub,
    COUNT(*)::INTEGER           AS djen_n_publicacoes,
    list(DISTINCT tribunal)     AS djen_tribunais
FROM manifest
WHERE length(regexp_replace(numero_processo, '[^0-9]', '', 'g')) = 20
GROUP BY nr_processo
"""

_JURIS_AGG_SQL = """
WITH ranked AS (
    SELECT
        regexp_replace(nr_processo, '[^0-9]', '', 'g') AS nr_processo,
        id_documento,
        tipo,
        data_julgamento,
        orgao,
        relator,
        classe_judicial,
        url_portal,
        ROW_NUMBER() OVER (
            PARTITION BY regexp_replace(nr_processo, '[^0-9]', '', 'g')
            ORDER BY
                CASE tipo
                    WHEN 'ACÓRDÃO' THEN 1
                    WHEN 'SENTENÇA' THEN 2
                    ELSE 9
                END,
                data_julgamento DESC NULLS LAST
        ) AS rn
    FROM tjro_juris
    WHERE length(regexp_replace(nr_processo, '[^0-9]', '', 'g')) = 20
),
principal AS (
    SELECT * FROM ranked WHERE rn = 1
),
agg AS (
    SELECT
        regexp_replace(nr_processo, '[^0-9]', '', 'g') AS nr_processo,
        COUNT(*)::INTEGER        AS juris_n_documentos,
        list(DISTINCT tipo)      AS juris_tipos,
        MAX(data_julgamento)     AS juris_data_julgamento,
    FROM tjro_juris
    WHERE length(regexp_replace(nr_processo, '[^0-9]', '', 'g')) = 20
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

_UNIFICADOS_SQL = """
WITH
    base AS (
        SELECT
            COALESCE(d.nr_processo, j.nr_processo, s.nr_processo) AS nr_processo,
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
            (CASE WHEN d.nr_processo IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN j.nr_processo IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN s.nr_processo IS NOT NULL THEN 1 ELSE 0 END)::INTEGER AS n_fontes,
            list_filter(
                ['djen', 'juris', 'stj'],
                x -> (
                    (x = 'djen'  AND d.nr_processo IS NOT NULL) OR
                    (x = 'juris' AND j.nr_processo IS NOT NULL) OR
                    (x = 'stj'   AND s.nr_processo IS NOT NULL)
                )
            ) AS fontes,
            NOW() AS updated_at
        FROM djen_agg d
        FULL OUTER JOIN juris_agg j USING (nr_processo)
        FULL OUTER JOIN stj_agg   s USING (nr_processo)
    )
SELECT
    nr_processo,
    -- Build display mask inline (20 digits → NNNNNNN-DD.AAAA.J.TR.OOOO)
    (nr_processo[1:7] || '-' || nr_processo[8:9] || '.' ||
     nr_processo[10:13] || '.' || nr_processo[14:14] || '.' ||
     nr_processo[15:16] || '.' || nr_processo[17:20]) AS nr_processo_mascara,
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
    fontes,
    n_fontes,
    updated_at
FROM base
ORDER BY nr_processo
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
    manifest_path = ensure_manifest()
    stj_path = ensure_stj_parquet()
    juris_files = juris_parquet_files()

    con = duckdb.connect()

    # Register manifest view
    con.execute(
        f"CREATE VIEW manifest AS SELECT * FROM read_csv_auto('{manifest_path}', header=true)"
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
    # DJEN: the sync-manifest is a caderno-level index (tribunal x date); it has no
    # numero_processo column. A future "comunicacoes" parquet (individual publication
    # records) would enable the DJEN contribution. Skip gracefully when absent.
    print("Building DJEN aggregation…")
    manifest_cols = {row[0] for row in con.execute("DESCRIBE manifest").fetchall()}
    if "numero_processo" in manifest_cols and "data_publicacao" in manifest_cols:
        con.execute(f"CREATE TEMP TABLE djen_agg AS {_DJEN_AGG_SQL}")
    else:
        print(
            "  SKIP: manifest lacks numero_processo/data_publicacao — "
            "DJEN contribution requires a comunicacoes parquet (not yet generated)",
            file=sys.stderr,
        )
        con.execute(
            "CREATE TEMP TABLE djen_agg AS "
            "SELECT NULL::VARCHAR AS nr_processo, NULL::DATE AS djen_primeira_pub, "
            "NULL::DATE AS djen_ultima_pub, NULL::INTEGER AS djen_n_publicacoes, "
            "NULL::VARCHAR[] AS djen_tribunais "
            "WHERE FALSE"
        )
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

    # Build processo_documentos (JURIS + STJ only; DJEN requires a future comunicacoes parquet)
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
