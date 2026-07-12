#!/usr/bin/env python3
"""Reconcile DJEN x TJRO JURIS x STJ into processos_unificados.

Pipeline:
  1. Load DJEN from every consolidated comunicacoes.parquet (discovered via the
     causaganha-catalog manifest) — GROUP BY nr_processo
  2. Load JURIS from tjro-juris-<year>.parquet files (local, or fetched from
     the tjro-juris-{year} IA items when absent locally) — GROUP BY nr_processo
  3. Load STJ from stj-acordaos.parquet — filter to CNJ numbers only
  4. Full outer join the three aggregations in DuckDB
  5. Optional DataJud enrichment (RFC 0010): LEFT JOIN the official capa
     (classe_oficial, assuntos, orgao_julgador, grau, data_ajuizamento,
     ultima_atualizacao, tem_datajud) when datajud-capa-*.parquet exists
     (local, or fetched from the datajud-{tribunal} IA items) — without it
     the columns are NULL/false and behaviour is unchanged
  6. Write processos_unificados.parquet + processo_documentos.parquet
  7. Write a source-coverage report (per-source counts + load status +
     fontes intersection matrix) next to the output as
     processos_unificados.report.json, and fail loudly when an expected
     source ended up with zero rows because it could not be loaded at all
  8. Upload both parquets to IA item causaganha-dashboard

Environment knobs:
  RECONCILE_CACHE_DIR          — where IA-fetched source parquets are cached
                                 (default: data/reconcile-cache)
  RECONCILE_DATAJUD_TRIBUNAIS  — comma list of datajud-{tribunal} IA items to
                                 probe for capa parquets (default: tjro)
  RECONCILE_EXPECTED_SOURCES   — comma list of sources whose *unavailability*
                                 is fatal (default: djen,juris,stj,datajud)
  RECONCILE_STRICT             — set to 0/false to never exit non-zero on
                                 unavailable expected sources (same as
                                 --no-strict)
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import httpx

from datajud.archive import CAPA_SCHEMA as _DATAJUD_CAPA_SCHEMA
from datajud.archive import capa_parquet_name as _datajud_capa_name
from datajud.archive import item_id as _datajud_item_id


ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

_PARQUET_UNIFICADOS = DATA_DIR / "processos_unificados.parquet"
_PARQUET_DOCUMENTOS = DATA_DIR / "processo_documentos.parquet"
_REPORT_NAME = "processos_unificados.report.json"

_IA_BASE = "https://archive.org/download"
_IA_METADATA_BASE = "https://archive.org/metadata"
_IA_SEARCH_URL = "https://archive.org/advancedsearch.php"
_IA_ITEM_DASHBOARD = "causaganha-dashboard"
_IA_CATALOG_MANIFEST_URL = f"{_IA_BASE}/causaganha-catalog/manifest.parquet"

_STJ_PARQUET = DATA_DIR / "stj" / "stj-acordaos.parquet"
_STJ_IA_URL = f"{_IA_BASE}/stj-acordaos-primeira-secao/stj-acordaos.parquet"

# DataJud capa parquets (datajud enrich CLI, RFC 0010) — optional enrichment.
_DATAJUD_DIR = DATA_DIR / "datajud"
_DEFAULT_DATAJUD_TRIBUNAIS = ("tjro",)

# TJRO JURIS yearly items on IA (see src/tjro_juris/archive.py). Both local
# glob spellings are honoured: the CLI/workflows write data/tjro-juris/,
# older docs said data/tjro_juris/.
_JURIS_ITEM_PREFIX = "tjro-juris"
_JURIS_ITEM_RE = re.compile(r"^tjro-juris-\d{4}$")
_JURIS_LOCAL_GLOBS = (
    "data/tjro_juris/*/tjro-juris-*.parquet",
    "data/tjro-juris/*/tjro-juris-*.parquet",
)

# ── Source load tracking ───────────────────────────────────────────────────────

SOURCE_NAMES = ("djen", "juris", "stj", "datajud")

STATUS_LOADED_LOCAL = "loaded_local"
STATUS_LOADED_REMOTE = "loaded_remote"
STATUS_UNAVAILABLE = "unavailable"


@dataclass
class SourceLoad:
    """How a reconciliation source was (or wasn't) loaded."""

    name: str
    status: str
    detail: str = ""
    rows: int = 0


def _cache_dir() -> Path:
    return Path(os.environ.get("RECONCILE_CACHE_DIR", "") or str(DATA_DIR / "reconcile-cache"))


def _datajud_tribunais() -> tuple[str, ...]:
    raw = os.environ.get("RECONCILE_DATAJUD_TRIBUNAIS", "")
    tribs = tuple(t.strip().lower() for t in raw.split(",") if t.strip())
    return tribs or _DEFAULT_DATAJUD_TRIBUNAIS


def _expected_sources() -> tuple[str, ...]:
    raw = os.environ.get("RECONCILE_EXPECTED_SOURCES", "")
    names = tuple(s.strip().lower() for s in raw.split(",") if s.strip())
    return names or SOURCE_NAMES


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
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    print(f"  saved to {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def _fetch_cached(client: httpx.Client, url: str, dest: Path, label: str) -> Path:
    """Download url to dest unless a previous run already cached it."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  cached: {dest}")
        return dest
    print(f"Downloading {label} from {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = client.get(url)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"  saved to {dest} ({dest.stat().st_size:,} bytes)")
    return dest


def _ia_item_files(client: httpx.Client, item_id: str) -> list[str]:
    """File names inside an IA item ([] when the item does not exist)."""
    resp = client.get(f"{_IA_METADATA_BASE}/{item_id}")
    resp.raise_for_status()
    files = resp.json().get("files", [])
    return [f["name"] for f in files if isinstance(f, dict) and "name" in f]


def comunicacoes_parquet_urls(con: duckdb.DuckDBPyConnection) -> list[str] | None:
    """URLs of every consolidated comunicacoes.parquet, from the IA catalog.

    consolidate-parquet.yml uploads one comunicacoes.parquet per consolidated
    date (item djen-YYYY-MM-DD); causaganha-catalog/manifest.parquet is the
    index of every such file across every item, kept fresh by
    update-catalog.yml. Querying it (instead of e.g. listing IA items
    directly) keeps this in sync with whatever has actually been consolidated
    without hand-enumerating dates.

    Returns None when the catalog itself could not be read (source
    *unavailable*), as opposed to [] (catalog readable, genuinely lists no
    comunicacoes parquets).
    """
    try:
        rows = con.execute(
            "SELECT DISTINCT ia_url FROM read_parquet(?) WHERE table_name = 'comunicacoes'",
            [_IA_CATALOG_MANIFEST_URL],
        ).fetchall()
    except duckdb.Error as exc:
        print(f"  WARNING: could not read IA catalog manifest — {exc}", file=sys.stderr)
        return None
    return sorted(r[0] for r in rows)


def ensure_stj_parquet() -> tuple[Path | None, SourceLoad]:
    if _STJ_PARQUET.exists():
        print(f"Using local STJ parquet: {_STJ_PARQUET}")
        return _STJ_PARQUET, SourceLoad("stj", STATUS_LOADED_LOCAL, str(_STJ_PARQUET))
    try:
        path = _download(_STJ_IA_URL, _STJ_PARQUET, "STJ parquet")
    except (httpx.HTTPError, OSError) as exc:
        print(f"  WARNING: could not download STJ parquet — {exc}", file=sys.stderr)
        return None, SourceLoad("stj", STATUS_UNAVAILABLE, f"IA download failed: {exc}")
    return path, SourceLoad("stj", STATUS_LOADED_REMOTE, _STJ_IA_URL)


def juris_parquet_files() -> list[Path]:
    files: set[Path] = set()
    for pattern in _JURIS_LOCAL_GLOBS:
        files.update(ROOT.glob(pattern))
    return sorted(files)


def _discover_juris_items(client: httpx.Client) -> list[str]:
    """tjro-juris-{year} item identifiers that actually exist on IA."""
    resp = client.get(
        _IA_SEARCH_URL,
        params={
            "q": f"identifier:{_JURIS_ITEM_PREFIX}-*",
            "fl[]": "identifier",
            "rows": "500",
            "output": "json",
        },
    )
    resp.raise_for_status()
    docs = resp.json().get("response", {}).get("docs", [])
    return sorted(
        d["identifier"]
        for d in docs
        if isinstance(d, dict) and _JURIS_ITEM_RE.match(d.get("identifier", ""))
    )


def fetch_juris_from_ia() -> tuple[list[Path], bool]:
    """Download JURIS parquets from the tjro-juris-{year} IA items.

    Prefers the consolidated tjro-juris-{year}.parquet when the item has one;
    otherwise falls back to the monthly shards the sync uploads. Returns
    (paths, needs_dedup) — monthly shards can overlap between crawls, so they
    must be deduplicated by id_documento before aggregation.
    """
    cache = _cache_dir() / "juris"
    paths: list[Path] = []
    needs_dedup = False
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        items = _discover_juris_items(client)
        if not items:
            print(f"  no {_JURIS_ITEM_PREFIX}-* items found on IA", file=sys.stderr)
            return [], False
        for item in items:
            names = _ia_item_files(client, item)
            consolidated = f"{item}.parquet"
            if consolidated in names:
                wanted = [consolidated]
            else:
                wanted = sorted(n for n in names if n.endswith(".parquet"))
                if wanted:
                    needs_dedup = True
            if not wanted:
                print(f"  IA item {item}: no parquet files", file=sys.stderr)
            paths.extend(
                _fetch_cached(
                    client, f"{_IA_BASE}/{item}/{name}", cache / item / name, f"JURIS {item}/{name}"
                )
                for name in wanted
            )
    return paths, needs_dedup


def ensure_juris_parquets() -> tuple[list[Path], bool, SourceLoad]:
    """JURIS parquets: local files first, IA fallback otherwise.

    Returns (paths, needs_dedup, load_status).
    """
    local = juris_parquet_files()
    if local:
        detail = f"{len(local)} local parquet file(s)"
        return local, False, SourceLoad("juris", STATUS_LOADED_LOCAL, detail)
    print(f"No local JURIS parquets — trying IA items {_JURIS_ITEM_PREFIX}-{{year}}")
    try:
        remote, needs_dedup = fetch_juris_from_ia()
    except (httpx.HTTPError, OSError) as exc:
        return [], False, SourceLoad("juris", STATUS_UNAVAILABLE, f"IA fetch failed: {exc}")
    if remote:
        detail = f"{len(remote)} parquet file(s) from IA {_JURIS_ITEM_PREFIX}-* items"
        return remote, needs_dedup, SourceLoad("juris", STATUS_LOADED_REMOTE, detail)
    detail = f"no local parquets and no parquets in IA {_JURIS_ITEM_PREFIX}-* items"
    return [], False, SourceLoad("juris", STATUS_UNAVAILABLE, detail)


def datajud_parquet_files() -> list[Path]:
    return sorted(_DATAJUD_DIR.glob("datajud-capa-*.parquet"))


def fetch_datajud_from_ia() -> list[Path]:
    """Download DataJud capa parquets from the datajud-{tribunal} IA items."""
    cache = _cache_dir() / "datajud"
    paths: list[Path] = []
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        for tribunal in _datajud_tribunais():
            item = _datajud_item_id(tribunal)
            filename = _datajud_capa_name(tribunal)
            names = _ia_item_files(client, item)
            if filename not in names:
                print(f"  IA item {item}: no {filename} (item missing or empty)", file=sys.stderr)
                continue
            paths.append(
                _fetch_cached(
                    client,
                    f"{_IA_BASE}/{item}/{filename}",
                    cache / filename,
                    f"DataJud {item}/{filename}",
                )
            )
    return paths


def ensure_datajud_parquets() -> tuple[list[Path], SourceLoad]:
    """DataJud capa parquets: local files first, IA fallback otherwise."""
    local = datajud_parquet_files()
    if local:
        detail = f"{len(local)} local parquet file(s)"
        return local, SourceLoad("datajud", STATUS_LOADED_LOCAL, detail)
    tribs = ", ".join(_datajud_item_id(t) for t in _datajud_tribunais())
    print(f"No local DataJud capa parquets — trying IA item(s) {tribs}")
    try:
        remote = fetch_datajud_from_ia()
    except (httpx.HTTPError, OSError) as exc:
        return [], SourceLoad("datajud", STATUS_UNAVAILABLE, f"IA fetch failed: {exc}")
    if remote:
        detail = f"{len(remote)} parquet file(s) from IA ({tribs})"
        return remote, SourceLoad("datajud", STATUS_LOADED_REMOTE, detail)
    detail = f"no local parquets and no capa parquet in IA item(s) {tribs}"
    return [], SourceLoad("datajud", STATUS_UNAVAILABLE, detail)


# ── IA upload ──────────────────────────────────────────────────────────────────


def upload_to_ia(path: Path, remote_name: str) -> None:
    """PUT a file to the causaganha-dashboard IA item via httpx."""
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


# ── Source coverage report & validation ───────────────────────────────────────


def validate_coverage(
    sources: dict[str, SourceLoad],
    expected: tuple[str, ...],
) -> tuple[list[str], list[str]]:
    """Distinguish "couldn't load the source" from "source genuinely empty".

    Returns (errors, warnings):
      - error   — an *expected* source ended with zero rows because it was
                  never loaded (status=unavailable): the reconciliation ran
                  blind on that source and the output silently degrades.
      - warning — a source loaded fine but contributed zero rows (legitimate
                  empty/zero-overlap), or a non-expected source unavailable.
    """
    errors: list[str] = []
    warnings: list[str] = []
    for name, load in sources.items():
        if load.status == STATUS_UNAVAILABLE and load.rows == 0:
            msg = f"source '{name}' has zero rows because it was NOT loaded — {load.detail}"
            (errors if name in expected else warnings).append(msg)
        elif load.rows == 0:
            warnings.append(
                f"source '{name}' loaded ({load.status}) but contributed zero processos"
                f" — {load.detail}"
            )
    return errors, warnings


def _emit_validation(errors: list[str], warnings: list[str]) -> None:
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    for msg in warnings:
        prefix = "::warning title=reconcile source coverage::" if in_ci else "WARNING: "
        print(f"{prefix}{msg}", file=sys.stderr)
    for msg in errors:
        prefix = "::error title=reconcile source coverage::" if in_ci else "ERROR: "
        print(f"{prefix}{msg}", file=sys.stderr)


def _print_report(report: dict[str, Any]) -> None:
    print("\n── Source coverage ──────────────────────────────────────────")
    for name, src in report["sources"].items():
        print(f"  {name:<8} {src['rows']:>12,} processos  {src['status']:<14} {src['detail']}")
    print("  Intersections (fontes → processos):")
    for combo, n in sorted(report["combinations"].items()):
        print(f"    {combo:<32} {n:>12,}")
    print(f"  total={report['total']:,}  multi_fonte={report['multi_fonte']:,}")


def _build_report(
    sources: dict[str, SourceLoad],
    combinations: dict[str, int],
    total: int,
    multi: int,
) -> dict[str, Any]:
    expected = _expected_sources()
    errors, warnings = validate_coverage(sources, expected)
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "total": total,
        "multi_fonte": multi,
        "sources": {
            name: {"rows": load.rows, "status": load.status, "detail": load.detail}
            for name, load in sources.items()
        },
        "combinations": combinations,
        "validation": {
            "expected_sources": list(expected),
            "errors": errors,
            "warnings": warnings,
        },
    }


# ── Main pipeline ──────────────────────────────────────────────────────────────


def _register_djen(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register the DJEN comunicacoes view.

    Union of every consolidated date, read straight off IA — there's no single
    local cache file for this, unlike STJ/JURIS, since it's one small parquet
    per consolidated date.
    """
    comunicacoes_urls = comunicacoes_parquet_urls(con)
    if comunicacoes_urls:
        url_list = ", ".join(f"'{u}'" for u in comunicacoes_urls)
        print(f"Registering DJEN comunicacoes view: {len(comunicacoes_urls)} parquet file(s)")
        con.execute(
            f"CREATE VIEW comunicacoes AS SELECT * FROM read_parquet([{url_list}], "
            "union_by_name=true)"
        )
        detail = f"{len(comunicacoes_urls)} comunicacoes parquet(s) via IA catalog"
        return SourceLoad("djen", STATUS_LOADED_REMOTE, detail)

    if comunicacoes_urls is None:
        load = SourceLoad("djen", STATUS_UNAVAILABLE, "IA catalog manifest unreadable")
    else:
        load = SourceLoad(
            "djen", STATUS_LOADED_REMOTE, "IA catalog readable but lists no comunicacoes parquets"
        )
    print(
        "WARNING: no comunicacoes.parquet available — DJEN contribution will be empty",
        file=sys.stderr,
    )
    con.execute(
        "CREATE VIEW comunicacoes AS "
        "SELECT NULL::VARCHAR AS numero_processo, NULL::DATE AS data_disponibilizacao, "
        "NULL::VARCHAR AS tribunal WHERE FALSE"
    )
    return load


def _register_juris(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register the JURIS view (yearly consolidated parquets, or IA fallback)."""
    juris_files, needs_dedup, load = ensure_juris_parquets()
    if juris_files:
        juris_list = ", ".join(f"'{p}'" for p in juris_files)
        print(f"Registering JURIS view: {len(juris_files)} parquet file(s)")
        if needs_dedup:
            # Monthly shards straight from IA may overlap between crawls —
            # dedup by id_documento exactly like tjro_juris.dedup.consolidate_year.
            con.execute(
                "CREATE VIEW tjro_juris AS "
                "SELECT * EXCLUDE (_rn) FROM ("
                "  SELECT *, ROW_NUMBER() OVER ("
                "    PARTITION BY id_documento ORDER BY extraido_em DESC NULLS LAST"
                "  ) AS _rn "
                f"  FROM read_parquet([{juris_list}], union_by_name=true) "
                "  WHERE id_documento IS NOT NULL"
                ") WHERE _rn = 1"
            )
        else:
            con.execute(f"CREATE VIEW tjro_juris AS SELECT * FROM read_parquet([{juris_list}])")
        return load

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
    return load


def _register_stj(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    stj_path, load = ensure_stj_parquet()
    if stj_path is not None:
        print(f"Registering STJ view: {stj_path}")
        con.execute(f"CREATE VIEW acordaos AS SELECT * FROM read_parquet('{stj_path}')")
        return load

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
    return load


def _register_datajud(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register datajud_capa (local parquets, IA fallback, or empty).

    Joins only when the parquet has the columns _DATAJUD_AGG_SQL needs;
    without it the datajud columns are NULL and tem_datajud is false. The
    empty fallback is derived from the producer's own pyarrow schema
    (datajud.archive.CAPA_SCHEMA) rather than hand-typed, so it can't drift
    from it — same pattern as scripts/render_queries.py's
    _synthetic_datajud_capa.
    """
    _datajud_required_cols = {
        "numero_processo",
        "classe_nome",
        "assuntos",
        "orgao_julgador",
        "grau",
        "data_ajuizamento",
        "ultima_atualizacao",
    }
    datajud_files, load = ensure_datajud_parquets()
    if datajud_files:
        datajud_list = ", ".join(f"'{p}'" for p in datajud_files)
        print(f"  Registering DataJud capa view: {len(datajud_files)} parquet file(s)")
        con.execute(f"CREATE VIEW datajud_capa AS SELECT * FROM read_parquet([{datajud_list}])")
        datajud_cols = {row[0] for row in con.execute("DESCRIBE datajud_capa").fetchall()}
        if _datajud_required_cols <= datajud_cols:
            return load
        missing = sorted(_datajud_required_cols - datajud_cols)
        print(
            f"  SKIP: datajud-capa-*.parquet missing column(s) {missing} — "
            "DataJud enrichment will be empty (incompatible/partial parquet?)",
            file=sys.stderr,
        )
        con.execute("DROP VIEW datajud_capa")
        con.register("datajud_capa", _DATAJUD_CAPA_SCHEMA.empty_table())
        return SourceLoad(
            "datajud", STATUS_UNAVAILABLE, f"parquet(s) missing required column(s) {missing}"
        )

    print(
        "  SKIP: no datajud-capa-*.parquet found — DataJud enrichment will be empty",
        file=sys.stderr,
    )
    con.register("datajud_capa", _DATAJUD_CAPA_SCHEMA.empty_table())
    return load


def reconcile(*, upload: bool = True) -> dict[str, Any]:
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs; LOAD httpfs;")
    except duckdb.Error as exc:
        print(
            f"  WARNING: could not load DuckDB httpfs — remote parquet reads may fail: {exc}",
            file=sys.stderr,
        )

    djen_load = _register_djen(con)
    juris_load = _register_juris(con)
    stj_load = _register_stj(con)

    # Build aggregation CTEs
    print("Building DJEN aggregation…")
    con.execute(f"CREATE TEMP TABLE djen_agg AS {_DJEN_AGG_SQL}")
    djen_load.rows = con.execute("SELECT COUNT(*) FROM djen_agg").fetchone()[0]
    print(f"  {djen_load.rows:,} DJEN processes")

    print("Building JURIS aggregation…")
    con.execute(f"CREATE TEMP TABLE juris_agg AS {_JURIS_AGG_SQL}")
    juris_load.rows = con.execute("SELECT COUNT(*) FROM juris_agg").fetchone()[0]
    print(f"  {juris_load.rows:,} JURIS processes")

    print("Building STJ aggregation…")
    con.execute(f"CREATE TEMP TABLE stj_agg AS {_STJ_AGG_SQL}")
    stj_load.rows = con.execute("SELECT COUNT(*) FROM stj_agg").fetchone()[0]
    print(f"  {stj_load.rows:,} STJ processes (with valid CNJ number)")

    print("Building DataJud aggregation…")
    datajud_load = _register_datajud(con)
    con.execute(f"CREATE TEMP TABLE datajud_agg AS {_DATAJUD_AGG_SQL}")
    datajud_load.rows = con.execute("SELECT COUNT(*) FROM datajud_agg").fetchone()[0]
    print(f"  {datajud_load.rows:,} DataJud processes")

    # Full outer join → processos_unificados
    print("Running full outer join…")
    con.execute(f"CREATE TEMP TABLE processos_unificados AS {_UNIFICADOS_SQL}")
    total = con.execute("SELECT COUNT(*) FROM processos_unificados").fetchone()[0]
    multi = con.execute("SELECT COUNT(*) FROM processos_unificados WHERE n_fontes >= 2").fetchone()[
        0
    ]
    print(f"  {total:,} unified processes ({multi:,} present in 2+ sources)")

    # Intersection matrix: how many processos carry each fontes combination
    combinations = dict(
        con.execute(
            "SELECT array_to_string(fontes, '+') AS combo, COUNT(*) "
            "FROM processos_unificados GROUP BY combo ORDER BY combo"
        ).fetchall()
    )

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

    # Source coverage report — printed, and persisted next to the output
    sources = {s.name: s for s in (djen_load, juris_load, stj_load, datajud_load)}
    report = _build_report(sources, combinations, total, multi)
    report_path = _PARQUET_UNIFICADOS.parent / _REPORT_NAME
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote coverage report: {report_path}")
    _print_report(report)
    _emit_validation(report["validation"]["errors"], report["validation"]["warnings"])

    if upload:
        upload_to_ia(_PARQUET_UNIFICADOS, "processos_unificados.parquet")
        if _PARQUET_DOCUMENTOS.exists():
            upload_to_ia(_PARQUET_DOCUMENTOS, "processo_documentos.parquet")

    return {
        "djen": djen_load.rows,
        "juris": juris_load.rows,
        "stj": stj_load.rows,
        "datajud": datajud_load.rows,
        "total": total,
        "multi_fonte": multi,
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Reconcile DJEN x JURIS x STJ processos")
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip uploading to Internet Archive",
    )
    parser.add_argument(
        "--no-strict",
        action="store_true",
        help="Do not exit non-zero when an expected source is unavailable "
        "(same as RECONCILE_STRICT=0)",
    )
    args = parser.parse_args(argv)

    stats = reconcile(upload=not args.no_upload)
    total = stats["total"]
    multi = stats["multi_fonte"]
    print(f"\nDone. {total:,} processos_unificados ({multi:,} multi-fonte).")

    errors = stats["report"]["validation"]["errors"]
    strict_env = os.environ.get("RECONCILE_STRICT", "1").strip().lower()
    strict = not args.no_strict and strict_env not in {"0", "false", "no"}
    if errors and strict:
        print(
            f"FATAL: {len(errors)} expected source(s) not loaded — failing "
            "(use --no-strict or RECONCILE_STRICT=0 to downgrade).",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
