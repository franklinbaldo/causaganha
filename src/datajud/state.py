"""Durable DataJud state across ephemeral runners.

The public Internet Archive item keeps capa and movimentos as convenient
canonical Parquet files, but incremental execution needs a stronger commit
boundary: manifest + both Parquets must be restored from the *same* generation.

``datajud-state-{tribunal}.zip`` is that boundary.  It is uploaded only after
both canonical Parquets succeed and contains the exact three files plus a
content-addressed ``state.json``.  A fresh runner restores the bundle before
selecting pending CNJs.  The first run after migration can bootstrap from the
two legacy canonical Parquets; a half-present legacy pair is an error, not an
empty dataset.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from datajud import archive


STATE_SCHEMA_VERSION = 1
STATE_METADATA_NAME = "state.json"


class RemoteStateError(RuntimeError):
    """Remote DataJud state exists or was expected but cannot be restored safely."""


@dataclass(frozen=True)
class RestoreResult:
    """Outcome of restoring the durable state into a local data directory."""

    status: Literal["restored", "legacy", "bootstrap"]
    generation: str = ""


@dataclass(frozen=True)
class PublishResult:
    """Outcome of publishing one coherent DataJud generation."""

    ok: bool
    failed_file: str | None = None
    generation: str = ""


def bundle_name(tribunal: str) -> str:
    """Canonical filename of the coherent state bundle for *tribunal*."""
    return f"datajud-state-{tribunal.lower()}.zip"


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _payload_names(tribunal: str) -> tuple[str, str, str]:
    return (
        archive.capa_parquet_name(tribunal),
        archive.movimentos_parquet_name(tribunal),
        "datajud-manifest.csv",
    )


def _generation(payloads: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(payloads):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(payloads[name])))
    return digest.hexdigest()


def build_bundle(
    capa_path: Path,
    movimentos_path: Path,
    manifest_path: Path,
    tribunal: str,
) -> tuple[bytes, str]:
    """Build a content-addressed state bundle from the three local artifacts."""
    expected_names = _payload_names(tribunal)
    paths = (capa_path, movimentos_path, manifest_path)
    payloads = {name: path.read_bytes() for name, path in zip(expected_names, paths, strict=True)}
    generation = _generation(payloads)
    metadata = {
        "schema_version": STATE_SCHEMA_VERSION,
        "tribunal": tribunal.lower(),
        "generation": generation,
        "files": {
            name: {"sha256": _sha256(content), "size": len(content)}
            for name, content in payloads.items()
        },
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as bundle:
        for name, content in payloads.items():
            bundle.writestr(name, content)
        bundle.writestr(
            STATE_METADATA_NAME,
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    return buffer.getvalue(), generation


def _parse_metadata(bundle: zipfile.ZipFile, tribunal: str) -> dict:
    try:
        raw = bundle.read(STATE_METADATA_NAME)
        metadata = json.loads(raw.decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        msg = "invalid DataJud state metadata"
        raise RemoteStateError(msg) from exc

    if metadata.get("schema_version") != STATE_SCHEMA_VERSION:
        msg = f"unsupported DataJud state schema: {metadata.get('schema_version')!r}"
        raise RemoteStateError(msg)
    if metadata.get("tribunal") != tribunal.lower():
        msg = "DataJud state tribunal does not match requested tribunal"
        raise RemoteStateError(msg)
    if not isinstance(metadata.get("files"), dict):
        msg = "DataJud state metadata has no file map"
        raise RemoteStateError(msg)
    return metadata


def _verified_payloads(content: bytes, tribunal: str) -> tuple[dict[str, bytes], str]:
    expected_names = _payload_names(tribunal)
    try:
        with zipfile.ZipFile(io.BytesIO(content), mode="r") as bundle:
            metadata = _parse_metadata(bundle, tribunal)
            payloads: dict[str, bytes] = {}
            for name in expected_names:
                file_meta = metadata["files"].get(name)
                if not isinstance(file_meta, dict):
                    msg = f"DataJud state metadata missing {name}"
                    raise RemoteStateError(msg)
                try:
                    payload = bundle.read(name)
                except KeyError as exc:
                    msg = f"DataJud state bundle missing {name}"
                    raise RemoteStateError(msg) from exc
                if len(payload) != file_meta.get("size") or _sha256(payload) != file_meta.get(
                    "sha256"
                ):
                    msg = f"DataJud state checksum mismatch for {name}"
                    raise RemoteStateError(msg)
                payloads[name] = payload
    except zipfile.BadZipFile as exc:
        msg = "invalid DataJud state bundle"
        raise RemoteStateError(msg) from exc

    generation = _generation(payloads)
    if generation != metadata.get("generation"):
        msg = "DataJud state generation does not match its payloads"
        raise RemoteStateError(msg)
    return payloads, generation


def _replace_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.restore")
    pending.write_bytes(content)
    pending.replace(path)


def restore_remote_state(data_dir: Path, tribunal: str) -> RestoreResult:
    """Restore one coherent generation, with a safe legacy bootstrap path.

    ``None`` from ``archive.download_file`` means an HTTP 404.  Any transport
    error or non-404 HTTP failure propagates and is converted to a nominal
    ``RemoteStateError`` by this boundary.
    """
    try:
        bundle = archive.download_file(bundle_name(tribunal), tribunal)
    except OSError as exc:
        msg = f"failed to download DataJud state bundle: {exc}"
        raise RemoteStateError(msg) from exc

    if bundle is not None:
        payloads, generation = _verified_payloads(bundle, tribunal)
        capa_name, movimentos_name, manifest_name = _payload_names(tribunal)
        _replace_file(data_dir / capa_name, payloads[capa_name])
        _replace_file(data_dir / movimentos_name, payloads[movimentos_name])
        _replace_file(data_dir / manifest_name, payloads[manifest_name])
        return RestoreResult(status="restored", generation=generation)

    capa_name, movimentos_name, _manifest_name = _payload_names(tribunal)
    try:
        legacy_capa = archive.download_file(capa_name, tribunal)
        legacy_movimentos = archive.download_file(movimentos_name, tribunal)
    except OSError as exc:
        msg = f"failed to inspect legacy DataJud state: {exc}"
        raise RemoteStateError(msg) from exc

    if legacy_capa is None and legacy_movimentos is None:
        return RestoreResult(status="bootstrap")
    if legacy_capa is None or legacy_movimentos is None:
        msg = "legacy DataJud state is incomplete: capa and movimentos must both exist"
        raise RemoteStateError(msg)

    _replace_file(data_dir / capa_name, legacy_capa)
    _replace_file(data_dir / movimentos_name, legacy_movimentos)
    return RestoreResult(status="legacy")


def publish_remote_state(
    capa_path: Path,
    movimentos_path: Path,
    manifest_path: Path,
    tribunal: str,
    ia_key: str,
    ia_secret: str,
) -> PublishResult:
    """Publish canonical Parquets, then commit the matching state bundle last."""
    bundle_content, generation = build_bundle(
        capa_path,
        movimentos_path,
        manifest_path,
        tribunal,
    )
    bundle_path = capa_path.parent / bundle_name(tribunal)
    bundle_path.write_bytes(bundle_content)
    try:
        for path in (capa_path, movimentos_path):
            if not archive.upload_file(path, tribunal, ia_key, ia_secret):
                return PublishResult(
                    ok=False,
                    failed_file=path.name,
                    generation=generation,
                )
        if not archive.upload_file(bundle_path, tribunal, ia_key, ia_secret):
            return PublishResult(
                ok=False,
                failed_file=bundle_path.name,
                generation=generation,
            )
    finally:
        bundle_path.unlink(missing_ok=True)
    return PublishResult(ok=True, generation=generation)
