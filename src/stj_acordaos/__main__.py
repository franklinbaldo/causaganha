"""CLI for the STJ acórdãos ingestão pipeline.

Manual execution
----------------
Discover + download all resources (ZIPs + monthly JSONs) and extract safely::

    uv run stj-acordaos download --data-dir data/stj --manifest-path data/stj/stj-manifest.csv

Dedup extracted JSONs into a parquet and upload sources + parquet to IA
(requires ``IA_ACCESS_KEY`` / ``IA_SECRET_KEY`` in the environment)::

    uv run --env-file ~/workspace/.env stj-acordaos upload --data-dir data/stj

Show manifest summary::

    uv run stj-acordaos status

When no local manifest exists, ``download`` first tries to restore it from
the public IA item so already-uploaded, unchanged resources are skipped;
``upload`` pushes the manifest back to IA.

In CI, ``.github/workflows/stj-sync.yml`` runs the same commands with
secrets injected, daily plus ``workflow_dispatch``.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import httpx
import typer

from stj_acordaos.archive import fetch_manifest
from stj_acordaos.client import (
    STJWAFBlockedError,
    download_resource,
    extract_zip,
    get_resource_list,
)
from stj_acordaos.manifest import ManifestSTJ


app = typer.Typer(
    name="stj-acordaos",
    help="STJ acórdãos ingestão pipeline — download, dedup, upload to IA.",
    no_args_is_help=True,
)

# Default paths relative to project root (can be overridden via options)
_DEFAULT_DATA_DIR = Path("data/stj")
_DEFAULT_MANIFEST = _DEFAULT_DATA_DIR / "stj-manifest.csv"
_DEFAULT_EXTRACT_DIR = _DEFAULT_DATA_DIR / "extracted"
_DEFAULT_PARQUET = _DEFAULT_DATA_DIR / "stj-acordaos.parquet"


def _classify_resource(fmt: str, url: str) -> str | None:
    """Classify a CKAN resource as "zip" or "json"; None when neither.

    The STJ dataset carries auxiliary resources (e.g. a "dicionário de
    dados" CSV) that are not acórdãos data — downloading those as if they
    were JSON produces a file DuckDB's ``read_json`` chokes on later. Only
    resources explicitly declared zip/json (by CKAN ``format`` or URL
    suffix) are downloaded; anything else is skipped.
    """
    fmt = fmt.lower()
    url_lower = url.lower()
    if fmt == "zip" or url_lower.endswith(".zip"):
        return "zip"
    if fmt == "json" or url_lower.endswith(".json"):
        return "json"
    return None


def _already_uploaded(manifest: ManifestSTJ, dest_name: str, last_modified: str) -> bool:
    """True when *dest_name* is already on IA, unchanged since *last_modified*."""
    existing = manifest.get(dest_name)
    return (
        existing is not None
        and existing.ia_status == "uploaded"
        and existing.data_extracao == last_modified
    )


def _download_one(
    resource: dict,
    manifest: ManifestSTJ,
    zip_dir: Path,
    extract_dir: Path,
) -> None:
    """Download, extract and record a single CKAN resource.

    Raises ``STJWAFBlockedError`` upward unchanged (fail-fast: once the WAF
    has blocked this runner, every further request will fail too — the
    caller must not keep grinding through the remaining resources).
    """
    url: str = resource.get("url", "")
    name: str = resource.get("name", "") or resource.get("id", "unknown")
    fmt: str = (resource.get("format") or "").lower()
    last_modified: str = resource.get("last_modified") or resource.get("created") or ""

    if not url:
        typer.echo(f"  SKIP {name}: no URL", err=True)
        return

    tipo = _classify_resource(fmt, url)
    if tipo is None:
        typer.echo(f"  SKIP {name}: unrecognized format {fmt!r} (not zip/json)", err=True)
        return
    dest = zip_dir / f"{name}.{tipo}"

    if _already_uploaded(manifest, dest.name, last_modified):
        typer.echo(f"  SKIP {name}: already uploaded to IA (unchanged since {last_modified})")
        return

    typer.echo(f"→ Downloading {name} ({tipo}) …")
    try:
        download_resource(url, dest)
    except STJWAFBlockedError:
        typer.echo("  FATAL: STJ WAF blocked this runner — aborting.", err=True)
        raise
    except (httpx.HTTPError, OSError) as exc:
        typer.echo(f"  ERROR: {exc}", err=True)
        return

    n_extracted = 0
    if tipo == "zip":
        typer.echo(f"  Extracting {dest.name} …")
        try:
            extracted = extract_zip(dest, extract_dir)
            n_extracted = len(extracted)
        except (zipfile.BadZipFile, OSError) as exc:
            typer.echo(f"  Extract ERROR: {exc}", err=True)

    manifest.upsert(
        arquivo=dest.name,
        tipo=tipo,
        data_extracao=last_modified,
        ia_status="",
        n_registros=n_extracted,
    )
    manifest.save()
    typer.echo(f"  Done ({n_extracted} files extracted).")


def _restore_manifest_best_effort(manifest_path: Path) -> None:
    """Restore the manifest from IA when absent; never abort the run on failure.

    IA can return a transient error (observed: 503, not 404, for an item
    that has simply never been created yet) for reasons unrelated to whether
    a manifest actually exists. Failing to restore only costs redundant
    re-downloads of already-uploaded resources — no data is lost — so it
    must never abort the run.
    """
    if manifest_path.exists():
        return
    try:
        fetch_manifest(manifest_path)
    except httpx.HTTPError as exc:
        typer.echo(f"WARNING: manifest restore failed ({exc}); starting fresh.", err=True)


@app.command()
def download(
    data_dir: Path = typer.Option(_DEFAULT_DATA_DIR, help="Directory to store downloads."),
    manifest_path: Path = typer.Option(_DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
) -> None:
    """Discover resources, download ZIPs + JSONs, and extract safely.

    Resources already uploaded to IA with an unchanged ``last_modified``
    (per the manifest, restored from IA when no local copy exists) are
    skipped, keeping scheduled runs on blank runners incremental.
    """
    _restore_manifest_best_effort(manifest_path)
    manifest = ManifestSTJ(manifest_path)
    manifest.load()

    resources = get_resource_list()
    if not resources:
        typer.echo("No resources found.", err=True)
        raise typer.Exit(1)

    zip_dir = data_dir / "zips"
    extract_dir = data_dir / "extracted"
    zip_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    for resource in resources:
        _download_one(resource, manifest, zip_dir, extract_dir)

    typer.echo(f"\nManifest saved to {manifest_path} ({len(manifest)} entries).")


@app.command()
def upload(
    data_dir: Path = typer.Option(_DEFAULT_DATA_DIR, help="Directory containing the parquet file."),
    parquet_path: Path = typer.Option(_DEFAULT_PARQUET, help="Parquet file to upload."),
    manifest_path: Path = typer.Option(_DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
    ia_key: str = typer.Option("", envvar="IA_ACCESS_KEY", help="IA S3 access key."),
    ia_secret: str = typer.Option("", envvar="IA_SECRET_KEY", help="IA S3 secret key."),
) -> None:
    """Upload the deduplicated parquet file to Internet Archive."""
    from stj_acordaos.archive import upload_parquet
    from stj_acordaos.dedup import dedup_acordaos

    if not ia_key or not ia_secret:
        typer.echo("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", err=True)
        raise typer.Exit(1)

    manifest = ManifestSTJ(manifest_path)
    manifest.load()

    # Collect all JSON sources: extracted from ZIP + monthly downloads
    extract_dir = data_dir / "extracted"
    zip_dir = data_dir / "zips"
    json_files = sorted(
        list(extract_dir.glob("*.json") if extract_dir.exists() else [])
        + list(zip_dir.glob("*.json") if zip_dir.exists() else [])
    )
    if json_files:
        typer.echo(f"Deduplicating {len(json_files)} JSON files → {parquet_path} …")
        count = dedup_acordaos(json_files, parquet_path)
        typer.echo(f"  {count:,} records after dedup.")
    elif not parquet_path.exists():
        # No local JSONs (every resource was already uploaded+unchanged and
        # `download` skipped it) and no local parquet (a blank runner never
        # restores it). If the manifest agrees nothing is pending, IA already
        # has the correct parquet from a prior run — there is genuinely
        # nothing to do, not an error.
        if manifest.get_pending_uploads():
            typer.echo("ERROR: No JSON files and no existing parquet to upload.", err=True)
            raise typer.Exit(1)
        typer.echo("Nothing new to upload — all resources already on IA.")
        return

    # Upload original source files (ZIPs + monthly JSONs). Preserve the
    # entry's data_extracao/n_registros stamped by `download` — the download
    # skip compares data_extracao against CKAN's last_modified.
    all_sources = sorted(zip_dir.glob("*") if zip_dir.exists() else [])
    for src in all_sources:
        typer.echo(f"Uploading source {src.name} …")
        ok = upload_parquet(src, ia_key, ia_secret)
        tipo_src = "zip" if src.suffix == ".zip" else "json"
        existing = manifest.get(src.name)
        manifest.upsert(
            arquivo=src.name,
            tipo=tipo_src,
            data_extracao=existing.data_extracao if existing else "",
            ia_status="uploaded" if ok else "",
            n_registros=existing.n_registros if existing else 0,
        )

    # Upload consolidated parquet
    typer.echo(f"Uploading {parquet_path.name} to IA item stj-acordaos-primeira-secao …")
    ok = upload_parquet(parquet_path, ia_key, ia_secret)

    manifest.upsert(
        arquivo=parquet_path.name,
        tipo="parquet",
        data_extracao="",
        ia_status="uploaded" if ok else "",
        n_registros=0,
    )
    manifest.save()

    # Push the manifest itself so a blank runner can restore it next run.
    typer.echo(f"Uploading {manifest_path.name} to IA …")
    manifest_ok = upload_parquet(manifest_path, ia_key, ia_secret)
    if not manifest_ok:
        typer.echo("WARNING: manifest upload failed (next run re-downloads).", err=True)

    if ok:
        typer.echo("Upload complete.")
    else:
        typer.echo("Upload FAILED.", err=True)
        raise typer.Exit(1)


@app.command()
def status(
    manifest_path: Path = typer.Option(_DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
) -> None:
    """Show a summary of the STJ manifest."""
    manifest = ManifestSTJ(manifest_path)
    count = manifest.load()

    if count == 0:
        typer.echo("Manifest is empty or not found.")
        return

    rows = manifest.to_df()
    uploaded = sum(1 for r in rows if r["ia_status"] == "uploaded")
    pending = count - uploaded

    typer.echo(f"STJ Manifest: {manifest_path}")
    typer.echo(f"  Total entries : {count}")
    typer.echo(f"  Uploaded to IA: {uploaded}")
    typer.echo(f"  Pending upload: {pending}")
    typer.echo("")
    for row in rows:
        typer.echo(
            f"  {row['arquivo']:40s}  {row['tipo']:6s}  {row['ia_status'] or 'pending':8s}"
            f"  {row['n_registros']:>8,} records"
        )


if __name__ == "__main__":
    app()
