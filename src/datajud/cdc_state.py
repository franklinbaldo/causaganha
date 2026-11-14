"""Durable DataJud CDC state across ephemeral runners (issues #1704, #1706).

A CDC run streams changed processes from a cursor, so a fresh runner that
starts without the previous cursor, canonical Parquets and resolution index
re-streams from zero and then *publishes its partial view over the complete
one*. This module gives the CDC the same commit boundary ``datajud.state``
gives the enrich path:

``datajud-cdc-state-{tribunal}.zip`` holds the checkpoint (as JSON), the two
canonical Parquets and the resolution index, each with size + SHA-256, plus a
content-addressed generation. It is uploaded **last**, only after every
artifact it vouches for was published, so its presence is the proof that the
cursor inside it is backed by published data.

Restore rules (fail closed):

* bundle present → verify every payload, then restore it ("restored");
* bundle absent (HTTP 404) → seed canonical/index from the loose files already
  published, so the first run cannot shrink them ("legacy"), or start empty
  when nothing was ever published ("bootstrap");
* anything else (transport error, bad checksum, half a legacy pair) →
  :class:`CdcStateError`. An unreachable remote is never treated as empty.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from datajud import archive


if TYPE_CHECKING:
    from pathlib import Path

    from datajud.cdc import CdcCheckpoint


CDC_STATE_SCHEMA_VERSION = 1
CHECKPOINT_NAME = "checkpoint.json"
METADATA_NAME = "state.json"


class CdcStateError(RuntimeError):
    """Remote CDC state exists or was expected but cannot be restored or published safely."""


@dataclass(frozen=True)
class CdcRestoreResult:
    """Outcome of restoring CDC state into local directories."""

    status: Literal["restored", "legacy", "bootstrap"]
    checkpoint: dict | None = None
    generation: str = ""


def bundle_name(tribunal: str) -> str:
    """Filename of the CDC commit bundle for *tribunal*."""
    return f"datajud-cdc-state-{tribunal.lower()}.zip"


def index_name(tribunal: str) -> str:
    """Filename of the CNJ resolution index for *tribunal*."""
    return f"indice_processos_{tribunal.lower()}.parquet"


def _data_names(tribunal: str) -> tuple[str, str, str]:
    return (
        archive.capa_parquet_name(tribunal),
        archive.movimentos_parquet_name(tribunal),
        index_name(tribunal),
    )


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _generation(payloads: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(payloads):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(_sha256(payloads[name])))
    return digest.hexdigest()


def build_bundle(
    checkpoint: CdcCheckpoint,
    data_paths: dict[str, Path],
    tribunal: str,
) -> tuple[bytes, str]:
    """Build the commit bundle from the checkpoint and the local data files.

    *data_paths* maps each published data filename to its local path. Only files
    that exist are included; the metadata lists exactly what is inside.
    """
    payloads: dict[str, bytes] = {
        CHECKPOINT_NAME: json.dumps(
            asdict(checkpoint), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"),
    }
    for name, path in data_paths.items():
        if path.exists():
            payloads[name] = path.read_bytes()
    generation = _generation(payloads)
    metadata = {
        "schema_version": CDC_STATE_SCHEMA_VERSION,
        "tribunal": tribunal.lower(),
        "generation": generation,
        "published_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "files": {name: {"sha256": _sha256(c), "size": len(c)} for name, c in payloads.items()},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as bundle:
        for name, content in payloads.items():
            bundle.writestr(name, content)
        bundle.writestr(
            METADATA_NAME,
            json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    return buffer.getvalue(), generation


def _raise(msg: str, cause: BaseException | None = None) -> None:
    if cause is not None:
        raise CdcStateError(msg) from cause
    raise CdcStateError(msg)


def _read_metadata(bundle: zipfile.ZipFile, tribunal: str) -> dict:
    try:
        metadata = json.loads(bundle.read(METADATA_NAME).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _raise("invalid DataJud CDC state metadata", exc)
    if metadata.get("schema_version") != CDC_STATE_SCHEMA_VERSION:
        _raise(f"unsupported DataJud CDC state schema: {metadata.get('schema_version')!r}")
    if metadata.get("tribunal") != tribunal.lower():
        _raise("DataJud CDC state tribunal does not match requested tribunal")
    files = metadata.get("files")
    if not isinstance(files, dict) or CHECKPOINT_NAME not in files:
        _raise("DataJud CDC state metadata has no checkpoint")
    return metadata


def verified_payloads(content: bytes, tribunal: str) -> tuple[dict[str, bytes], str]:
    """Return the bundle payloads after checking every size, hash and the generation."""
    allowed = {CHECKPOINT_NAME, *_data_names(tribunal)}
    try:
        with zipfile.ZipFile(io.BytesIO(content), mode="r") as bundle:
            metadata = _read_metadata(bundle, tribunal)
            payloads: dict[str, bytes] = {}
            for name, meta in metadata["files"].items():
                if name not in allowed:
                    _raise(f"unexpected file in DataJud CDC state: {name}")
                try:
                    payload = bundle.read(name)
                except KeyError as exc:
                    _raise(f"DataJud CDC state bundle missing {name}", exc)
                if len(payload) != meta.get("size") or _sha256(payload) != meta.get("sha256"):
                    _raise(f"DataJud CDC state checksum mismatch for {name}")
                payloads[name] = payload
    except zipfile.BadZipFile as exc:
        _raise("invalid DataJud CDC state bundle", exc)
    generation = _generation(payloads)
    if generation != metadata.get("generation"):
        _raise("DataJud CDC state generation does not match its payloads")
    return payloads, generation


def _replace_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.restore")
    pending.write_bytes(content)
    pending.replace(path)


def _download(name: str, tribunal: str) -> bytes | None:
    try:
        return archive.download_file(name, tribunal)
    except OSError as exc:
        _raise(f"failed to download {name} from Internet Archive: {exc}", exc)
    return None  # pragma: no cover — _raise always raises


def restore_cdc_state(
    tribunal: str,
    *,
    canonical_dir: Path,
    index_dir: Path,
) -> CdcRestoreResult:
    """Restore the last published CDC generation into the local directories."""
    capa_name, mov_name, idx_name = _data_names(tribunal)
    targets = {
        capa_name: canonical_dir / capa_name,
        mov_name: canonical_dir / mov_name,
        idx_name: index_dir / idx_name,
    }

    bundle = _download(bundle_name(tribunal), tribunal)
    if bundle is not None:
        payloads, generation = verified_payloads(bundle, tribunal)
        for name, path in targets.items():
            if name in payloads:
                _replace_file(path, payloads[name])
        checkpoint = json.loads(payloads[CHECKPOINT_NAME].decode("utf-8"))
        return CdcRestoreResult(status="restored", checkpoint=checkpoint, generation=generation)

    # No commit bundle yet: never let the first run shrink what is already
    # published. Seed from the loose files; a half-present canonical pair is
    # an error, not an empty dataset.
    capa = _download(capa_name, tribunal)
    mov = _download(mov_name, tribunal)
    if capa is None and mov is None:
        return CdcRestoreResult(status="bootstrap")
    if capa is None or mov is None:
        _raise(
            "published DataJud canonical state is incomplete: capa and movimentos must both exist"
        )
    _replace_file(targets[capa_name], capa)
    _replace_file(targets[mov_name], mov)
    index = _download(idx_name, tribunal)
    if index is not None:
        _replace_file(targets[idx_name], index)
    return CdcRestoreResult(status="legacy")
