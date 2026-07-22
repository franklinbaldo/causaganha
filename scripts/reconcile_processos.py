#!/usr/bin/env python3
"""Reconcile DJEN x TJRO JURIS x STJ x DataJud into a cross-source index.

RFC 0014 M2 design: `indice_processual.parquet` is a THIN index — one row
per (numero_processo, fonte, registro_id), pointing at where the real
record lives (`arquivo_ia_url`) — never a denormalized copy of each
source's content fields. This generalizes the pattern DJEN's own
`processos` table already used (see `causaganha/consolidate/
schema_registry.py`'s SCHEMA_V3): each source keeps its natural schema in
its own already-published parquet; only cross-referencing them is new.
There is deliberately no second, independently-published "wide" parquet —
consumers (processo_consultar, web/src/lib/processoCnj.ts) join the index
against each source's own parquet at query time.

Pipeline:
  1. Load DJEN from every consolidated comunicacoes.parquet (discovered via
     the causaganha-catalog manifest) — flat, no GROUP BY.
  2. Load JURIS from tjro-juris-<year>.parquet files (local, or fetched from
     the tjro-juris-{year} IA items when absent locally) — flat.
  3. Load STJ from stj-acordaos.parquet — filter to CNJ numbers only, flat.
  4. Load DataJud capa (RFC 0010) from datajud-capa-*.parquet when present —
     flat; registro_id is synthesized (md5 of the composite natural key
     numero_processo+grau+orgao, since DataJud's own ES _id already encodes
     exactly that composite — see datajud/dedup.py's capa_row_key). DataJud
     movimentos are out of scope (no natural key at all, not indexed here).
  5. UNION ALL the four into indice_processual — never collapsed/aggregated.
  6. Write indice_processual.parquet.
  7. Write a source-coverage report (per-source distinct-process counts +
     load status + fontes intersection matrix) next to the output as
     indice_processual.report.json, and fail loudly when an expected source
     ended up with zero rows because it could not be loaded at all.
  8. Upload the parquet + report to IA item causaganha-dashboard.

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

_PARQUET_INDICE = DATA_DIR / "indice_processual.parquet"
_REPORT_NAME = "indice_processual.report.json"

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


class SourceDataError(Exception):
    """A source's parquet file(s) could not be read (corrupt/invalid/truncated).

    Distinct from httpx/OSError (transport failures) and duckdb.Error (raised
    directly by SQL execution) — this is raised by our own validation step so
    callers can catch exactly "the bytes we have are not usable parquet"
    without swallowing unrelated programming errors.
    """


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


# ── Data acquisition ───────────────────────────────────────────────────────────


def _is_valid_parquet(path: Path) -> bool:
    """Cheap structural check: can DuckDB even open this as parquet?

    Does not guarantee the *content* is semantically correct (e.g. expected
    columns) — callers that care about that still validate downstream. This
    only catches "not parquet at all" / truncated-file corruption.
    """
    con = duckdb.connect()
    try:
        con.execute(f"SELECT 1 FROM read_parquet('{path}') LIMIT 0")
    except duckdb.Error:
        return False
    else:
        return True
    finally:
        con.close()


def _quarantine(path: Path) -> None:
    """Remove an invalid *cached* file so future runs re-fetch instead of reusing it.

    Only ever called on files under our own cache directory — never on a
    local parquet the operator placed there themselves (see
    ensure_juris_parquets / ensure_datajud_parquets / ensure_stj_parquet,
    which never route operator-provided local files through this).
    """
    try:
        path.unlink(missing_ok=True)
        print(f"  quarantined invalid cache file: {path}", file=sys.stderr)
    except OSError as exc:
        print(f"  WARNING: could not remove invalid cache file {path} — {exc}", file=sys.stderr)


def _atomic_download(client: httpx.Client, url: str, dest: Path, label: str) -> None:
    """Download url to dest atomically: write to dest.part, then rename in place.

    A crash or truncated transfer never leaves a partial/corrupt file at
    `dest` itself — only a stray `.part` file, which is never treated as a
    cache hit (see _fetch_cached). Raises SourceDataError if the completed
    download is not readable as parquet.
    """
    print(f"Downloading {label} from {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    resp = client.get(url)
    resp.raise_for_status()
    tmp.write_bytes(resp.content)
    if not _is_valid_parquet(tmp):
        tmp.unlink(missing_ok=True)
        msg = f"downloaded file from {url} is not valid parquet"
        raise SourceDataError(msg)
    tmp.replace(dest)
    print(f"  saved to {dest} ({dest.stat().st_size:,} bytes)")


def _download(url: str, dest: Path, label: str) -> Path:
    with httpx.Client(timeout=180, follow_redirects=True) as client:
        _atomic_download(client, url, dest, label)
    return dest


def _fetch_cached(client: httpx.Client, url: str, dest: Path, label: str) -> Path:
    """Download url to dest unless a previous run already cached a valid copy.

    A cached file that fails validation (corrupt / truncated by an
    interrupted earlier run) is quarantined and re-fetched immediately —
    it is never silently treated as good just because it exists and is
    non-empty.
    """
    if dest.exists() and dest.stat().st_size > 0:
        if _is_valid_parquet(dest):
            print(f"  cached: {dest}")
            return dest
        print(f"  cached file failed validation, re-fetching: {dest}", file=sys.stderr)
        _quarantine(dest)
    _atomic_download(client, url, dest, label)
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
    except (httpx.HTTPError, OSError, SourceDataError) as exc:
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
    except (httpx.HTTPError, OSError, SourceDataError) as exc:
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
    except (httpx.HTTPError, OSError, SourceDataError) as exc:
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

# ── Cross-source index (RFC 0014 M2) ────────────────────────────────────────────
#
# Generalizes the pattern DJEN's own `processos` table already used (see
# schema_registry.py's SCHEMA_V3): a thin per-record index — one row per
# (numero_processo, fonte, registro_id) — never a collapsed/aggregated join.
# Each source keeps its own natural schema in its own already-published
# parquet (comunicacoes, tjro-juris-{year}, stj-acordaos, datajud-capa-
# {tribunal}); this index only says which records exist for a CNJ and where
# to find them (`arquivo_ia_url`). Consumers (processo_consultar,
# web/src/lib/processoCnj.ts) join back into the source parquet themselves —
# never a second, independently-published source of truth.
#
# DataJud capa has no single-column natural key (its own ES `_id` encodes a
# composite `{TRIBUNAL}_{classe}_{grau}_{orgao}_{numero}` — see
# datajud/dedup.py's capa_row_key) — registro_id is a deterministic md5 hash
# of that same composite, mirroring how DJEN's own comunicacao_id is a
# uuid5 hash of a composite key (transforms.py's djen_uuid5), just via
# DuckDB's built-in md5() instead of a custom UDF.
#
# DataJud movimentos are out of scope here: reconcile_processos.py never
# read them even in the old processos_unificados/processo_documentos shape,
# and unlike every other source they have no natural key at all, not even a
# composite one (ties on data_hora are real) — indexing them is a genuine
# follow-up, not a mechanical generalization of what already existed.

_INDICE_DJEN_SQL = """
SELECT
    regexp_replace(numero_processo, '[^0-9]', '', 'g') AS numero_processo,
    'djen' AS fonte,
    id AS registro_id,
    tribunal,
    data_disponibilizacao AS data,
    'https://archive.org/download/' || p_item_ia || '/comunicacoes.parquet' AS arquivo_ia_url
FROM comunicacoes
WHERE length(regexp_replace(numero_processo, '[^0-9]', '', 'g')) = 20
"""

_INDICE_JURIS_SQL = """
SELECT
    regexp_replace(nr_processo, '[^0-9]', '', 'g') AS numero_processo,
    'juris' AS fonte,
    id_documento::VARCHAR AS registro_id,
    'TJRO' AS tribunal,
    TRY_CAST(data_julgamento AS DATE) AS data,
    'https://archive.org/download/tjro-juris-' ||
        CAST(EXTRACT(YEAR FROM TRY_CAST(data_julgamento AS DATE)) AS VARCHAR) || '/tjro-juris-' ||
        CAST(EXTRACT(YEAR FROM TRY_CAST(data_julgamento AS DATE)) AS VARCHAR) || '.parquet'
        AS arquivo_ia_url
FROM tjro_juris
WHERE length(regexp_replace(nr_processo, '[^0-9]', '', 'g')) = 20
"""

_INDICE_STJ_SQL = """
SELECT
    regexp_replace("numeroProcesso", '[^0-9]', '', 'g') AS numero_processo,
    'stj' AS fonte,
    id::VARCHAR AS registro_id,
    'STJ' AS tribunal,
    TRY_CAST("dataDecisao" AS DATE) AS data,
    'https://archive.org/download/stj-acordaos-primeira-secao/stj-acordaos.parquet'
        AS arquivo_ia_url
FROM acordaos
WHERE length(regexp_replace("numeroProcesso", '[^0-9]', '', 'g')) = 20
"""

_INDICE_DATAJUD_SQL = """
SELECT
    regexp_replace(numero_processo, '[^0-9]', '', 'g') AS numero_processo,
    'datajud' AS fonte,
    md5(
        numero_processo || ':' || grau || ':' ||
        COALESCE(orgao_julgador_codigo::VARCHAR, 'nome:' || COALESCE(orgao_julgador, ''))
    ) AS registro_id,
    tribunal,
    TRY_CAST(ultima_atualizacao AS DATE) AS data,
    'https://archive.org/download/datajud-' || lower(tribunal) || '/datajud-capa-' ||
        lower(tribunal) || '.parquet' AS arquivo_ia_url
FROM datajud_capa
WHERE length(regexp_replace(numero_processo, '[^0-9]', '', 'g')) = 20
"""

_INDICE_SQL = f"""
SELECT *, NOW() AS updated_at FROM (
    {_INDICE_DJEN_SQL}
    UNION ALL
    {_INDICE_JURIS_SQL}
    UNION ALL
    {_INDICE_STJ_SQL}
    UNION ALL
    {_INDICE_DATAJUD_SQL}
)
ORDER BY numero_processo, fonte
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


def _empty_comunicacoes_view(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP VIEW IF EXISTS comunicacoes")
    con.execute(
        "CREATE VIEW comunicacoes AS "
        "SELECT NULL::VARCHAR AS numero_processo, NULL::DATE AS data_disponibilizacao, "
        "NULL::VARCHAR AS tribunal, NULL::VARCHAR AS id, NULL::VARCHAR AS p_item_ia "
        "WHERE FALSE"
    )


def _empty_juris_view(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP VIEW IF EXISTS tjro_juris")
    con.execute(
        "CREATE VIEW tjro_juris AS "
        "SELECT NULL::VARCHAR AS nr_processo, NULL::INTEGER AS id_documento, "
        "NULL::VARCHAR AS tipo, NULL::DATE AS data_julgamento, "
        "NULL::VARCHAR AS orgao, NULL::VARCHAR AS relator, "
        "NULL::VARCHAR AS classe_judicial, NULL::VARCHAR AS url_portal, "
        "NULL::VARCHAR AS texto_limpo "
        "WHERE FALSE"
    )


def _empty_acordaos_view(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("DROP VIEW IF EXISTS acordaos")
    con.execute(
        "CREATE VIEW acordaos AS "
        'SELECT NULL::VARCHAR AS "numeroProcesso", NULL::VARCHAR AS id, '
        'NULL::VARCHAR AS "siglaClasse", NULL::VARCHAR AS "ministroRelator", '
        'NULL::VARCHAR AS "tema", NULL::VARCHAR AS "teseJuridica", '
        'NULL::VARCHAR AS "ementa", NULL::DATE AS "dataDecisao", '
        'NULL::DATE AS "dataPublicacao" '
        "WHERE FALSE"
    )


def _quarantine_if_cached(files: list[Path], load: SourceLoad) -> None:
    """Quarantine *files* only when they came from our own IA-fetch cache.

    Never touches a local parquet the operator placed there themselves
    (status loaded_local) — only STATUS_LOADED_REMOTE means these paths are
    under _cache_dir(), populated by _fetch_cached/_download.
    """
    if load.status != STATUS_LOADED_REMOTE:
        return
    for path in files:
        _quarantine(path)


def _register_djen(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register the DJEN comunicacoes view.

    Union of every consolidated date, read straight off IA — there's no single
    local cache file for this, unlike STJ/JURIS, since it's one small parquet
    per consolidated date. A read failure here (e.g. one corrupt date among
    many) makes the WHOLE DJEN source unavailable for this run rather than
    crashing the reconciliation — the other sources still contribute.
    """
    comunicacoes_urls = comunicacoes_parquet_urls(con)
    if comunicacoes_urls:
        url_list = ", ".join(f"'{u}'" for u in comunicacoes_urls)
        print(f"Registering DJEN comunicacoes view: {len(comunicacoes_urls)} parquet file(s)")
        try:
            con.execute(
                f"CREATE VIEW comunicacoes AS SELECT * FROM read_parquet([{url_list}], "
                "union_by_name=true)"
            )
            con.execute("SELECT COUNT(*) FROM comunicacoes")  # force read now, not mid-aggregation
        except duckdb.Error as exc:
            print(f"  WARNING: DJEN parquet(s) unreadable — {exc}", file=sys.stderr)
            _empty_comunicacoes_view(con)
            detail = (
                f"parquet read failed for {len(comunicacoes_urls)} comunicacoes file(s) via IA "
                f"catalog: {type(exc).__name__}: {exc}"
            )
            return SourceLoad("djen", STATUS_UNAVAILABLE, detail)
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
    _empty_comunicacoes_view(con)
    return load


def _register_juris(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register the JURIS view (yearly consolidated parquets, or IA fallback).

    A read failure (corrupt/invalid parquet) makes JURIS unavailable for this
    run — the typed-empty fallback view is (re)created so the rest of the
    pipeline (aggregation, join) proceeds unaffected, and IA-cached files
    implicated in the failure are quarantined so the NEXT run re-fetches
    instead of hitting the same wall forever.
    """
    juris_files, needs_dedup, load = ensure_juris_parquets()
    if juris_files:
        juris_list = ", ".join(f"'{p}'" for p in juris_files)
        print(f"Registering JURIS view: {len(juris_files)} parquet file(s)")
        try:
            if needs_dedup:
                # Monthly shards straight from IA may overlap between crawls —
                # dedup by id_documento exactly like
                # tjro_juris.dedup.consolidate_year. Rows with a null
                # id_documento (extraction bug) are excluded rather than
                # collapsed together under a shared null key.
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
            con.execute("SELECT COUNT(*) FROM tjro_juris")  # force read now, not mid-aggregation
        except duckdb.Error as exc:
            print(f"  WARNING: JURIS parquet(s) unreadable — {exc}", file=sys.stderr)
            _quarantine_if_cached(juris_files, load)
            _empty_juris_view(con)
            files_desc = ", ".join(str(p) for p in juris_files)
            detail = f"parquet read failed for [{files_desc}]: {type(exc).__name__}: {exc}"
            return SourceLoad("juris", STATUS_UNAVAILABLE, detail)
        return load

    print(
        "WARNING: no JURIS parquets found — JURIS contribution will be empty",
        file=sys.stderr,
    )
    _empty_juris_view(con)
    return load


def _register_stj(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register the STJ acordaos view (local file or IA fallback).

    A read failure makes STJ unavailable for this run instead of crashing
    the reconciliation; an IA-cached file implicated in the failure is
    quarantined so the next run re-fetches.
    """
    stj_path, load = ensure_stj_parquet()
    if stj_path is not None:
        print(f"Registering STJ view: {stj_path}")
        try:
            con.execute(f"CREATE VIEW acordaos AS SELECT * FROM read_parquet('{stj_path}')")
            con.execute("SELECT COUNT(*) FROM acordaos")  # force read now, not mid-aggregation
        except duckdb.Error as exc:
            print(f"  WARNING: STJ parquet unreadable ({stj_path}) — {exc}", file=sys.stderr)
            _quarantine_if_cached([stj_path], load)
            _empty_acordaos_view(con)
            detail = f"parquet read failed for {stj_path}: {type(exc).__name__}: {exc}"
            return SourceLoad("stj", STATUS_UNAVAILABLE, detail)
        return load

    print("WARNING: STJ parquet unavailable — STJ contribution will be empty", file=sys.stderr)
    _empty_acordaos_view(con)
    return load


def _register_datajud(con: duckdb.DuckDBPyConnection) -> SourceLoad:
    """Register datajud_capa (local parquets, IA fallback, or empty).

    Joins only when the parquet has the columns _INDICE_DATAJUD_SQL needs;
    without those columns this source contributes nothing. The
    empty fallback is derived from the producer's own pyarrow schema
    (datajud.archive.CAPA_SCHEMA) rather than hand-typed, so it can't drift
    from it — same pattern as scripts/render_queries.py's
    _synthetic_datajud_capa. A read failure (corrupt/invalid parquet) makes
    DataJud unavailable for this run rather than crashing the reconciliation;
    an IA-cached file implicated in the failure is quarantined.
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
        try:
            con.execute(f"CREATE VIEW datajud_capa AS SELECT * FROM read_parquet([{datajud_list}])")
            datajud_cols = {row[0] for row in con.execute("DESCRIBE datajud_capa").fetchall()}
        except duckdb.Error as exc:
            print(f"  WARNING: DataJud parquet(s) unreadable — {exc}", file=sys.stderr)
            con.execute("DROP VIEW IF EXISTS datajud_capa")
            _quarantine_if_cached(datajud_files, load)
            con.register("datajud_capa", _DATAJUD_CAPA_SCHEMA.empty_table())
            files_desc = ", ".join(str(p) for p in datajud_files)
            detail = f"parquet read failed for [{files_desc}]: {type(exc).__name__}: {exc}"
            return SourceLoad("datajud", STATUS_UNAVAILABLE, detail)
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
    datajud_load = _register_datajud(con)

    # Cross-source index — flat, one row per (numero_processo, fonte,
    # registro_id), never collapsed. See _INDICE_SQL's own comment for the
    # design rationale (RFC 0014 M2: generalizes DJEN's own `processos`
    # table instead of introducing a second, denormalized source of truth).
    print("Building indice_processual…")
    con.execute(f"CREATE TEMP TABLE indice_processual AS {_INDICE_SQL}")

    # rows-per-source, for the coverage report, means "distinct processes
    # this source touched" (comparable across sources with very different
    # records-per-process ratios), not raw index row count.
    for load in (djen_load, juris_load, stj_load, datajud_load):
        load.rows = con.execute(
            "SELECT COUNT(DISTINCT numero_processo) FROM indice_processual WHERE fonte = ?",
            [load.name],
        ).fetchone()[0]
        print(f"  {load.rows:,} {load.name} processes")

    total = con.execute("SELECT COUNT(DISTINCT numero_processo) FROM indice_processual").fetchone()[
        0
    ]
    multi = con.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT numero_processo FROM indice_processual"
        "  GROUP BY numero_processo HAVING COUNT(DISTINCT fonte) >= 2"
        ")"
    ).fetchone()[0]
    print(f"  {total:,} unified processes ({multi:,} present in 2+ sources)")

    # Intersection matrix: how many processos carry each fontes combination —
    # one row per process (not per index row), so a process with e.g. 40
    # DJEN comunicações still counts once, not 40 times.
    combinations = dict(
        con.execute(
            "SELECT combo, COUNT(*) FROM ("
            "  SELECT array_to_string(list(DISTINCT fonte ORDER BY fonte), '+') AS combo "
            "  FROM indice_processual GROUP BY numero_processo"
            ") GROUP BY combo ORDER BY combo"
        ).fetchall()
    )

    # Write indice_processual.parquet
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing {_PARQUET_INDICE}")
    con.execute(f"COPY indice_processual TO '{_PARQUET_INDICE}' (FORMAT PARQUET, COMPRESSION ZSTD)")

    # Source coverage report — printed, and persisted next to the output
    sources = {s.name: s for s in (djen_load, juris_load, stj_load, datajud_load)}
    report = _build_report(sources, combinations, total, multi)
    report_path = _PARQUET_INDICE.parent / _REPORT_NAME
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote coverage report: {report_path}")
    _print_report(report)
    _emit_validation(report["validation"]["errors"], report["validation"]["warnings"])

    if upload:
        upload_to_ia(_PARQUET_INDICE, "indice_processual.parquet")
        # RFC 0014 M2: processo_consultar needs the coverage report remotely
        # too, to distinguish "source loaded but had no rows for this CNJ"
        # from "source was unavailable when the dataset was generated" —
        # both used to look identical (absent from the index) without it.
        upload_to_ia(report_path, _REPORT_NAME)

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
