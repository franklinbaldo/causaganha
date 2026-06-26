"""CLI for the STJ acórdãos ingestão pipeline."""

from __future__ import annotations

from pathlib import Path

import typer


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


@app.command()
def download(
    data_dir: Path = typer.Option(_DEFAULT_DATA_DIR, help="Directory to store downloads."),
    manifest_path: Path = typer.Option(_DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
) -> None:
    """Discover resources, download ZIPs + JSONs, and extract safely."""
    from stj_acordaos.client import download_resource, extract_zip, get_resource_list
    from stj_acordaos.manifest import ManifestSTJ

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
        url: str = resource.get("url", "")
        name: str = resource.get("name", "") or resource.get("id", "unknown")
        fmt: str = (resource.get("format") or "").lower()
        last_modified: str = resource.get("last_modified") or resource.get("created") or ""

        if not url:
            typer.echo(f"  SKIP {name}: no URL", err=True)
            continue

        tipo = "zip" if fmt == "zip" or url.lower().endswith(".zip") else "json"
        dest = zip_dir / f"{name}.{tipo}"

        typer.echo(f"→ Downloading {name} ({tipo}) …")
        try:
            download_resource(url, dest)
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"  ERROR: {exc}", err=True)
            continue

        n_extracted = 0
        if tipo == "zip":
            typer.echo(f"  Extracting {dest.name} …")
            try:
                extracted = extract_zip(dest, extract_dir)
                n_extracted = len(extracted)
            except Exception as exc:  # noqa: BLE001
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
    from stj_acordaos.manifest import ManifestSTJ

    if not ia_key or not ia_secret:
        typer.echo("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", err=True)
        raise typer.Exit(1)

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
        typer.echo("ERROR: No JSON files and no existing parquet to upload.", err=True)
        raise typer.Exit(1)

    if not parquet_path.exists():
        typer.echo(f"ERROR: Parquet not found at {parquet_path}.", err=True)
        raise typer.Exit(1)

    manifest = ManifestSTJ(manifest_path)
    manifest.load()

    # Upload original source files (ZIPs + monthly JSONs)
    all_sources = sorted(zip_dir.glob("*") if zip_dir.exists() else [])
    for src in all_sources:
        typer.echo(f"Uploading source {src.name} …")
        ok = upload_parquet(src, ia_key, ia_secret)
        tipo_src = "zip" if src.suffix == ".zip" else "json"
        manifest.upsert(
            arquivo=src.name,
            tipo=tipo_src,
            data_extracao="",
            ia_status="uploaded" if ok else "",
            n_registros=0,
        )
        manifest.save()

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
    from stj_acordaos.manifest import ManifestSTJ

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
