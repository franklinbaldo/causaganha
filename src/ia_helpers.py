"""
Internet Archive Helper Functions and Configuration
"""

import asyncio
import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import typer  # For typer.echo, consider passing a logger or callback for messages

# Assuming config_data is loaded similarly to how it's done in cli.py
# This might need adjustment if ia_helpers.py cannot directly access cli.py's config_data
# For now, let's try to load it here as well.
# If this causes issues (e.g. circular dependency if config needs DB path that DB init needs config),
# then config values might need to be passed into these functions from cli.py.

try:
    from config import load_config

    config_data = load_config()
except ImportError:
    # Fallback or default config if running standalone or config.py is not found
    config_data = {
        "internet_archive": {
            "master_item_id": "causaganha_diarios_collection_fallback",
            "metadata_filename": "file_level_metadata_fallback.json",
            "max_concurrent_uploads": 2,
        },
        "database": {"path": "data/causaganha_fallback.duckdb"},  # Example
    }
    print(
        "Warning: Could not load from config.py, using fallback IA/DB config values in ia_helpers."
    )


MASTER_IA_ITEM_ID = config_data.get("internet_archive", {}).get(
    "master_item_id", "causaganha_diarios_collection"
)
IA_METADATA_FILENAME = config_data.get("internet_archive", {}).get(
    "metadata_filename", "file_level_metadata.json"
)
IA_DEFAULT_ITEM_METADATA = {
    "collection": "opensource",
    "mediatype": "texts",
    "creator": "CausaGanha",
    "title": "CausaGanha - Coleção de Diários Oficiais Judiciais",
}

ia_executor = ThreadPoolExecutor(
    max_workers=config_data.get("internet_archive", {}).get("max_concurrent_uploads", 2)
)
log_main_ops = True  # Global toggle for high-level logging, can be made configurable


async def execute_ia_command_async(
    ia_command_args: List[str], log_output: bool = True
) -> bool:
    """
    Executes an 'ia' command asynchronously.
    Prepends 'ia' to the command_args.
    """
    loop = asyncio.get_event_loop()
    full_command = ["ia"] + ia_command_args
    command_str_for_logging = " ".join(full_command)

    try:
        if log_output and log_main_ops:
            typer.echo(f"🔩 IA CMD: {command_str_for_logging}")

        result = await loop.run_in_executor(
            ia_executor,
            lambda: subprocess.run(
                full_command, capture_output=True, text=True, check=False, timeout=900
            ),
        )

        if result.returncode == 0:
            if log_output and log_main_ops:
                typer.echo(
                    f"✅ IA OK: {command_str_for_logging.split(' ')[1] if len(command_str_for_logging.split(' ')) > 1 else ''}"
                )
                if (
                    result.stdout and log_output
                ):  # Only show if verbose logging for this command is on
                    typer.echo(f"   Output: {result.stdout[:150].strip()}...")
            return True
        else:
            if log_output and log_main_ops:  # Always log errors if main logging is on
                typer.echo(
                    f"❌ IA FAIL (code {result.returncode}): {command_str_for_logging}",
                    err=True,
                )
                if result.stderr:
                    typer.echo(f"   Stderr: {result.stderr.strip()}", err=True)
                if result.stdout:
                    typer.echo(f"   Stdout: {result.stdout.strip()}", err=True)
            return False
    except subprocess.TimeoutExpired:
        if log_main_ops:
            typer.echo(f"❌ IA TIMEOUT: {command_str_for_logging}", err=True)
        return False
    except Exception as e:
        if log_main_ops:
            typer.echo(
                f"❌ IA EXCEPTION {command_str_for_logging}: {type(e).__name__} - {e}",
                err=True,
            )
        return False


async def execute_ia_upload_async(
    target_ia_id: str,
    local_filepath: Path,
    remote_filename: str,
    item_metadata: Optional[Dict[str, str]] = None,
    log_output: bool = True,
) -> bool:
    if not local_filepath.exists():
        if log_output and log_main_ops:
            typer.echo(f"❌ UploadFAIL: File {local_filepath} not found.", err=True)
        return False

    ia_args = [
        "upload",
        target_ia_id,
        str(local_filepath),
        f"--remote-name={remote_filename}",
    ]
    final_item_metadata = {}
    if target_ia_id == MASTER_IA_ITEM_ID:
        final_item_metadata.update(IA_DEFAULT_ITEM_METADATA)
    if item_metadata:
        final_item_metadata.update(item_metadata)
    for key, value in final_item_metadata.items():
        ia_args.append(f"--metadata={key}:{value}")

    return await execute_ia_command_async(ia_args, log_output=log_output)


async def archive_diario_to_master_item(
    local_pdf_path: Path, tribunal_code: str, pdf_filename_on_ia: str
) -> Tuple[Optional[str], Optional[str]]:
    master_id = MASTER_IA_ITEM_ID
    remote_ia_full_path = f"{tribunal_code}/{pdf_filename_on_ia}"

    if log_main_ops:
        typer.echo(
            f"📦 Archiving '{local_pdf_path.name}' to IA master '{master_id}' as '{remote_ia_full_path}'"
        )

    upload_successful = await execute_ia_upload_async(
        target_ia_id=master_id,
        local_filepath=local_pdf_path,
        remote_filename=remote_ia_full_path,
    )

    if upload_successful:
        if log_main_ops:
            typer.echo(f"✅ Archived OK: '{master_id}/{remote_ia_full_path}'")
        return master_id, remote_ia_full_path
    else:
        if log_main_ops:
            typer.echo(
                f"❌ ArchiveFAIL: '{local_pdf_path.name}' to master item.", err=True
            )
        return None, None


async def download_ia_file_async(
    item_id: str,
    remote_filename_on_ia: str,
    destination_dir: Path,
    log_output: bool = True,
) -> Optional[Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    local_filename = Path(remote_filename_on_ia).name
    local_filepath = destination_dir / local_filename

    ia_args = [
        "download",
        item_id,
        remote_filename_on_ia,
        "--destdir",
        str(destination_dir),
    ]

    if log_output and log_main_ops:
        typer.echo(
            f"⬇️  Downloading '{remote_filename_on_ia}' from IA '{item_id}' to '{local_filepath}'"
        )

    success = await execute_ia_command_async(ia_args, log_output=log_output)

    if success and local_filepath.exists() and local_filepath.is_file():
        if log_output and log_main_ops:
            typer.echo(f"✅ Download OK: '{local_filepath}'")
        return local_filepath
    else:
        if log_output and log_main_ops:
            typer.echo(
                f"❌ DownloadFAIL: '{remote_filename_on_ia}' from IA '{item_id}'. Target '{local_filepath}' not found/not file.",
                err=True,
            )
        if local_filepath.exists():
            try:
                local_filepath.unlink()
            except OSError:
                pass
        return None


async def update_ia_file_level_metadata_summary(
    master_ia_id: str, file_remote_path: str, new_file_metadata_entry: Dict[str, Any]
) -> bool:
    summary_json_filename = IA_METADATA_FILENAME
    current_summary_data: Dict[str, Any] = {}

    if log_main_ops:
        typer.echo(
            f"🔄 MetaUPDATE: For '{file_remote_path}' in '{master_ia_id}/{summary_json_filename}'"
        )

    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        downloaded_summary_filepath = await download_ia_file_async(
            master_ia_id, summary_json_filename, tmp_dir, log_output=False
        )
        if downloaded_summary_filepath and downloaded_summary_filepath.exists():
            try:
                with open(downloaded_summary_filepath, "r", encoding="utf-8") as f:
                    current_summary_data = json.load(f)
                if log_main_ops:
                    typer.echo(f"📄 MetaDL OK: Parsed '{summary_json_filename}'.")
            except Exception as e:  # Catch JSONDecodeError and other read errors
                if log_main_ops:
                    typer.echo(
                        f"⚠️ MetaDL WARN: Corrupt/unreadable '{summary_json_filename}': {e}. Creating new.",
                        err=True,
                    )
        else:
            if log_main_ops:
                typer.echo(
                    f"📄 MetaDL INFO: '{summary_json_filename}' not found on IA. Creating new."
                )

    current_summary_data[file_remote_path] = new_file_metadata_entry
    if log_main_ops:
        typer.echo(f"📊 MetaLocalUPDATE: Entry for '{file_remote_path}'.")

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".json", encoding="utf-8"
    ) as tmp_upload_file:
        json.dump(current_summary_data, tmp_upload_file, ensure_ascii=False, indent=2)
        temp_upload_filepath = Path(tmp_upload_file.name)

    if log_main_ops:
        typer.echo(f"📝 MetaLocalSAVE: Updated summary at '{temp_upload_filepath}'")

    upload_successful = await execute_ia_upload_async(
        master_ia_id, temp_upload_filepath, summary_json_filename, log_output=False
    )
    try:
        temp_upload_filepath.unlink()
    except OSError as e:
        if log_main_ops:
            typer.echo(
                f"⚠️ MetaCleanupWARN: Could not del temp upload file '{temp_upload_filepath}': {e}",
                err=True,
            )

    if upload_successful:
        if log_main_ops:
            typer.echo(
                f"✅ MetaUpload OK: '{summary_json_filename}' to '{master_ia_id}'."
            )
        return True
    else:
        if log_main_ops:
            typer.echo(
                f"❌ MetaUploadFAIL: '{summary_json_filename}' to '{master_ia_id}'.",
                err=True,
            )
        return False
