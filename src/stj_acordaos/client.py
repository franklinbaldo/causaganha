"""HTTP client for the STJ open data portal (CKAN API)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import httpx
import structlog


log = structlog.get_logger()

PORTAL_URL = "https://dadosabertos.web.stj.jus.br/dataset/espelhos-de-acordaos-primeira-secao"
DATASET_API_URL = (
    "https://dadosabertos.web.stj.jus.br/api/3/action/package_show"
    "?id=a96a175b-a54b-4bfd-82b8-fcd7cc0200bc"
)


def _make_client() -> httpx.Client:
    """Create a configured synchronous HTTP client."""
    return httpx.Client(
        timeout=120,
        follow_redirects=True,
        headers={"User-Agent": "causaganha/stj-backup (+https://github.com/franklinbaldo/causaganha)"},
    )


def get_resource_list() -> list[dict]:
    """Fetch the resource list from the STJ CKAN dataset API.

    Returns a list of resource dicts with keys like ``url``, ``name``,
    ``format``, ``last_modified``, etc.
    """
    with _make_client() as client:
        resp = client.get(DATASET_API_URL)
        resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        msg = f"CKAN API returned success=false: {data.get('error')}"
        raise RuntimeError(msg)
    resources: list[dict] = data.get("result", {}).get("resources", [])
    log.info("stj_resource_list_fetched", count=len(resources))
    return resources


def download_resource(url: str, dest_path: Path) -> None:
    """Download a resource file (ZIP or JSON) to *dest_path*.

    Streams the response to avoid loading large files into memory.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with _make_client() as client, client.stream("GET", url) as resp:
        resp.raise_for_status()
        with dest_path.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=65536):
                fh.write(chunk)
    log.info("stj_resource_downloaded", url=url, dest=str(dest_path), size=dest_path.stat().st_size)


def _safe_member(member: zipfile.ZipInfo) -> bool:
    """Return True if the ZIP member is safe to extract.

    Rejects:
    - Members with ``..`` in their path (path traversal)
    - Absolute paths
    - Non-JSON files
    """
    name = member.filename
    if ".." in name or name.startswith("/"):
        return False
    return name.lower().endswith(".json")


def extract_zip(zip_path: Path, dest_dir: Path) -> list[Path]:
    """Safely extract JSON files from a ZIP archive.

    Validates all member paths before extraction. Only ``.json`` files
    are extracted; path-traversal members are skipped with a warning.

    Returns a list of extracted file paths.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            if not _safe_member(member):
                log.warning("stj_zip_skipped_member", member=member.filename, zip=str(zip_path))
                continue
            out_path = dest_dir / Path(member.filename).name
            out_path.write_bytes(zf.read(member.filename))
            extracted.append(out_path)
    log.info("stj_zip_extracted", zip=str(zip_path), count=len(extracted), dest=str(dest_dir))
    return extracted
