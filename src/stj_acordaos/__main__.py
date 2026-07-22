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

import sys
from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from stj_acordaos import service


app = App(
    name="stj-acordaos",
    help="STJ acórdãos ingestão pipeline — download, dedup, upload to IA.",
)


def _echo_download_outcome(outcome: service.DownloadOutcome) -> None:
    if outcome.action == "skip_no_url":
        print(f"  SKIP {outcome.dest_name}: no URL", file=sys.stderr)
    elif outcome.action == "skip_unrecognized_format":
        print(
            f"  SKIP {outcome.dest_name}: unrecognized format {outcome.detail!r} (not zip/json)",
            file=sys.stderr,
        )
    elif outcome.action == "skip_already_uploaded":
        print(
            f"  SKIP {outcome.dest_name}: already uploaded to IA (unchanged since {outcome.detail})"
        )
    elif outcome.action == "download_error":
        print(f"  ERROR: {outcome.detail}", file=sys.stderr)
    else:
        if outcome.action == "extract_error":
            print(f"  Extract ERROR: {outcome.detail}", file=sys.stderr)
        print(f"  Done ({outcome.n_extracted} files extracted).")


@app.command
def download(
    data_dir: Annotated[
        Path, Parameter(help="Directory to store downloads.")
    ] = service.DEFAULT_DATA_DIR,
    manifest_path: Annotated[
        Path, Parameter(help="Path to stj-manifest.csv.")
    ] = service.DEFAULT_MANIFEST,
) -> int:
    """Discover resources, download ZIPs + JSONs, and extract safely.

    Resources already uploaded to IA with an unchanged ``last_modified``
    (per the manifest, restored from IA when no local copy exists) are
    skipped, keeping scheduled runs on blank runners incremental.
    """
    summary = service.download_all(data_dir, manifest_path)
    if summary is None:
        print("No resources found.", file=sys.stderr)
        return 1

    for outcome in summary.outcomes:
        _echo_download_outcome(outcome)

    print(f"\nManifest saved to {manifest_path} ({summary.manifest_entries} entries).")
    return 0


@app.command
def upload(
    data_dir: Annotated[
        Path, Parameter(help="Directory containing the parquet file.")
    ] = service.DEFAULT_DATA_DIR,
    parquet_path: Annotated[
        Path, Parameter(help="Parquet file to upload.")
    ] = service.DEFAULT_PARQUET,
    manifest_path: Annotated[
        Path, Parameter(help="Path to stj-manifest.csv.")
    ] = service.DEFAULT_MANIFEST,
) -> int:
    """Upload the deduplicated parquet file to Internet Archive."""
    ia_key, ia_secret = service.ia_credentials()
    if not ia_key or not ia_secret:
        print("ERROR: IA_ACCESS_KEY and IA_SECRET_KEY must be set.", file=sys.stderr)
        return 1

    result = service.upload_all(data_dir, parquet_path, manifest_path, ia_key, ia_secret)

    if result.status == "nothing_to_do":
        print("Nothing new to upload — all resources already on IA.")
        return 0
    if result.status == "no_data":
        print("ERROR: No JSON files and no existing parquet to upload.", file=sys.stderr)
        return 1

    if result.ok:
        print("Upload complete.")
        return 0
    print("Upload FAILED.", file=sys.stderr)
    return 1


@app.command
def status(
    manifest_path: Annotated[
        Path, Parameter(help="Path to stj-manifest.csv.")
    ] = service.DEFAULT_MANIFEST,
) -> None:
    """Show a summary of the STJ manifest."""
    summary = service.manifest_summary(manifest_path)

    if summary.count == 0:
        print("Manifest is empty or not found.")
        return

    print(f"STJ Manifest: {manifest_path}")
    print(f"  Total entries : {summary.count}")
    print(f"  Uploaded to IA: {summary.uploaded}")
    print(f"  Pending upload: {summary.pending}")
    print()
    for row in summary.rows:
        print(
            f"  {row['arquivo']:40s}  {row['tipo']:6s}  {row['ia_status'] or 'pending':8s}"
            f"  {row['n_registros']:>8,} records"
        )


if __name__ == "__main__":
    app()
