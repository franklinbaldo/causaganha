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

Business logic lives in ``stj_acordaos.service`` (RFC 0013 Fase 2); this
module only parses argv and echoes results. ``IA_ACCESS_KEY``/
``IA_SECRET_KEY`` are read from the environment only — not CLI options —
so they never appear in ``--help`` or in a future MCP tool's schema.
"""

from __future__ import annotations

from pathlib import Path

import typer

from stj_acordaos import service


app = typer.Typer(
    name="stj-acordaos",
    help="STJ acórdãos ingestão pipeline — download, dedup, upload to IA.",
    no_args_is_help=True,
)


def _echo_download_outcome(outcome: service.DownloadOutcome) -> None:
    if outcome.action == "skip_no_url":
        typer.echo(f"  SKIP {outcome.dest_name}: no URL", err=True)
    elif outcome.action == "skip_unrecognized_format":
        typer.echo(
            f"  SKIP {outcome.dest_name}: unrecognized format {outcome.detail!r} (not zip/json)",
            err=True,
        )
    elif outcome.action == "skip_already_uploaded":
        typer.echo(
            f"  SKIP {outcome.dest_name}: already uploaded to IA (unchanged since {outcome.detail})"
        )
    elif outcome.action == "download_error":
        typer.echo(f"  ERROR: {outcome.detail}", err=True)
    else:
        if outcome.action == "extract_error":
            typer.echo(f"  Extract ERROR: {outcome.detail}", err=True)
        typer.echo(f"  Done ({outcome.n_extracted} files extracted).")


@app.command()
def download(
    data_dir: Path = typer.Option(service.DEFAULT_DATA_DIR, help="Directory to store downloads."),
    manifest_path: Path = typer.Option(service.DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
) -> None:
    """Discover resources, download ZIPs + JSONs, and extract safely.

    Resources already uploaded to IA with an unchanged ``last_modified``
    (per the manifest, restored from IA when no local copy exists) are
    skipped, keeping scheduled runs on blank runners incremental.
    """
    summary = service.download_all(data_dir, manifest_path)
    if summary is None:
        typer.echo("No resources found.", err=True)
        raise typer.Exit(1)

    for outcome in summary.outcomes:
        _echo_download_outcome(outcome)

    typer.echo(f"\nManifest saved to {manifest_path} ({summary.manifest_entries} entries).")


@app.command()
def upload(
    data_dir: Path = typer.Option(
        service.DEFAULT_DATA_DIR, help="Directory containing the parquet file."
    ),
    parquet_path: Path = typer.Option(service.DEFAULT_PARQUET, help="Parquet file to upload."),
    manifest_path: Path = typer.Option(service.DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
) -> None:
    """Upload the deduplicated parquet file to Internet Archive."""
    ia_key, ia_secret = service.ia_credentials()
    if not ia_key or not ia_secret:
        typer.echo("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", err=True)
        raise typer.Exit(1)

    result = service.upload_all(data_dir, parquet_path, manifest_path, ia_key, ia_secret)

    if result.status == "nothing_to_do":
        typer.echo("Nothing new to upload — all resources already on IA.")
        return
    if result.status == "no_data":
        typer.echo("ERROR: No JSON files and no existing parquet to upload.", err=True)
        raise typer.Exit(1)

    if result.ok:
        typer.echo("Upload complete.")
    else:
        typer.echo("Upload FAILED.", err=True)
        raise typer.Exit(1)


@app.command()
def status(
    manifest_path: Path = typer.Option(service.DEFAULT_MANIFEST, help="Path to stj-manifest.csv."),
) -> None:
    """Show a summary of the STJ manifest."""
    summary = service.manifest_summary(manifest_path)

    if summary.count == 0:
        typer.echo("Manifest is empty or not found.")
        return

    typer.echo(f"STJ Manifest: {manifest_path}")
    typer.echo(f"  Total entries : {summary.count}")
    typer.echo(f"  Uploaded to IA: {summary.uploaded}")
    typer.echo(f"  Pending upload: {summary.pending}")
    typer.echo("")
    for row in summary.rows:
        typer.echo(
            f"  {row['arquivo']:40s}  {row['tipo']:6s}  {row['ia_status'] or 'pending':8s}"
            f"  {row['n_registros']:>8,} records"
        )


if __name__ == "__main__":
    app()
