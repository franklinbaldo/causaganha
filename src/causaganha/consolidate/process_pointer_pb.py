"""Small dependency-free protobuf-wire codec for the per-process locator schema.

Wire layout is defined in process_pointer.proto; all fields are length-delimited
except positive numeric IDs and schema_version. Unknown protobuf fields are
skipped, with malformed inputs rejected. Does not contain original document text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

VERSION = 1
PUB_FIELDS = ("data", "membro_json", "comunicacao_id", "hash")
DJ_FIELDS = (
    "tribunal",
    "grau",
    "documento_id",
    "item_ia",
    "arquivo_zip",
    "membro",
    "atualizado_em",
)


def _varint(value: int) -> bytes:
    if not isinstance(value, int) or value < 0 or value >= 1 << 64:
        raise ValueError("Invalid protobuf unsigned integer")
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    for i in range(10):
        if pos >= len(data):
            raise ValueError("Truncated protobuf varint")
        byte = data[pos]
        pos += 1
        if i == 9 and byte > 1:
            raise ValueError("Protobuf varint overflow")
        result |= (byte & 127) << (7 * i)
        if not byte & 128:
            return result, pos
    raise ValueError("Protobuf varint too long")


def _field(number: int, data: bytes) -> bytes:
    return _varint((number << 3) | 2) + _varint(len(data)) + data


def _text(number: int, value: Any) -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"Expected text for field {number}")
    return _field(number, value.encode("utf-8"))


def _fields(data: bytes):
    pos = 0
    while pos < len(data):
        tag, pos = _read_varint(data, pos)
        number, kind = tag >> 3, tag & 7
        if number == 0:
            raise ValueError("Protobuf field zero is invalid")
        if kind == 0:
            value, pos = _read_varint(data, pos)
        elif kind == 2:
            length, pos = _read_varint(data, pos)
            if length > len(data) - pos:
                raise ValueError("Truncated protobuf field")
            value = data[pos : pos + length]
            pos += length
        elif kind == 1:
            if pos + 8 > len(data):
                raise ValueError("Truncated fixed64")
            value = data[pos : pos + 8]
            pos += 8
        elif kind == 5:
            if pos + 4 > len(data):
                raise ValueError("Truncated fixed32")
            value = data[pos : pos + 4]
            pos += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type {kind}")
        yield number, kind, value


def _encode_publication(row: tuple[str, str, str, str]) -> bytes:
    day, member, identity, dj_hash = row
    identity_value = int(identity)
    if identity_value < 0:
        raise ValueError("Negative DJEN communication ID")
    return (
        _text(1, day)
        + _text(2, member)
        + _varint(3 << 3)
        + _varint(identity_value)
        + _text(4, dj_hash)
    )


def _encode_datajud(document: dict[str, str]) -> bytes:
    return b"".join(
        _text(number, document[name]) for number, name in enumerate(DJ_FIELDS, start=1)
    )


def encode_index(
    publications: list[tuple[str, str, str, str]],
    datajud: list[dict[str, str]] | None = None,
) -> bytes:
    """Deterministic v1 encoding; duplicate pointers are eliminated."""
    encoded = [_field(1, _encode_publication(row)) for row in sorted(set(publications))]
    identities = set()
    for document in sorted(
        datajud or [],
        key=lambda d: (d["tribunal"], d["grau"], d["documento_id"]),
    ):
        key = (document["tribunal"], document["grau"], document["documento_id"])
        if key in identities:
            raise ValueError(f"Duplicate DataJud identity: {key}")
        identities.add(key)
        encoded.append(_field(2, _encode_datajud(document)))
    encoded.append(_varint(15 << 3) + _varint(VERSION))
    return b"".join(encoded)


def _decode_publication(data: bytes) -> tuple[str, str, str, str]:
    result: dict[int, str] = {}
    for number, kind, value in _fields(data):
        if number == 3 and kind == 0:
            result[number] = str(value)
        elif number in (1, 2, 4) and kind == 2:
            result[number] = value.decode("utf-8")
    if any(n not in result for n in range(1, 5)):
        raise ValueError("Incomplete DJEN pointer")
    return (result[1], result[2], result[3], result[4])


def _decode_datajud(data: bytes) -> dict[str, str]:
    result = {}
    for number, kind, value in _fields(data):
        if 1 <= number <= len(DJ_FIELDS) and kind == 2:
            result[DJ_FIELDS[number - 1]] = value.decode("utf-8")
    if any(name not in result for name in DJ_FIELDS):
        raise ValueError("Incomplete DataJud pointer")
    return result


def decode_index(data: bytes) -> dict[str, Any]:
    """Return both pointer families. Refuse unversioned/unknown versions."""
    publications = []
    datajud = []
    version = None
    for number, kind, value in _fields(data):
        if number == 1 and kind == 2:
            publications.append(_decode_publication(value))
        elif number == 2 and kind == 2:
            datajud.append(_decode_datajud(value))
        elif number == 15 and kind == 0:
            version = value
    if version != VERSION:
        raise ValueError(f"Unsupported process-index schema version: {version}")
    return {"publicacoes": publications, "datajud": datajud}


def _timestamp(value: str) -> datetime:
    """Require an offset-aware ISO timestamp for ordering DataJud snapshots."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid DataJud timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("DataJud timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def update_datajud(
    previous: list[dict[str, str]], incoming: list[dict[str, str]]
) -> list[dict[str, str]]:
    """Keep the newest pointer *per document identity*, not per CNJ."""
    rows = {(r["tribunal"], r["grau"], r["documento_id"]): r for r in previous}
    for row in incoming:
        key = (row["tribunal"], row["grau"], row["documento_id"])
        prior = rows.get(key)
        if prior is None or _timestamp(row["atualizado_em"]) > _timestamp(
            prior["atualizado_em"]
        ):
            rows[key] = row
        elif (
            _timestamp(row["atualizado_em"]) == _timestamp(prior["atualizado_em"])
            and row != prior
        ):
            raise ValueError(f"Conflicting DataJud snapshots at same timestamp: {key}")
    return [rows[key] for key in sorted(rows)]
