"""Experimental adapters for processo.proto, with reversible residuals.

The typed fields carry the document. Residual JSON carries only fields/defaults
that the existing proto3 schema cannot express exactly. No raw-document copy is
stored alongside the typed document. This is a demonstration, not a production
storage decision.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import demo_pb2
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message


def json_bytes(value: Any) -> bytes:
    """A common, deterministic JSON encoding for baselines and residuals."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def fill(message: Message, values: dict[str, Any]) -> None:
    """Project expressible values into native protobuf fields; residuals cover the rest."""
    for field in message.DESCRIPTOR.fields:
        value = values.get(field.name)
        if field.is_repeated:
            if isinstance(value, list):
                target = getattr(message, field.name)
                for item in value:
                    if field.type == FieldDescriptor.TYPE_MESSAGE:
                        fill(target.add(), item if isinstance(item, dict) else {})
                    elif isinstance(item, str):
                        target.append(item)
        elif field.type == FieldDescriptor.TYPE_MESSAGE:
            if isinstance(value, dict):
                fill(getattr(message, field.name), value)
        elif field.type == FieldDescriptor.TYPE_STRING:
            if isinstance(value, str):
                setattr(message, field.name, value)
        elif field.type == FieldDescriptor.TYPE_BOOL:
            if isinstance(value, bool):
                setattr(message, field.name, value)
        elif field.type == FieldDescriptor.TYPE_DOUBLE:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if isinstance(value, float) or abs(value) <= 2**53:
                    setattr(message, field.name, value)
        elif isinstance(value, int) and not isinstance(value, bool):
            bits = (
                32
                if field.type in (FieldDescriptor.TYPE_INT32, FieldDescriptor.TYPE_UINT32)
                else 64
            )
            signed = field.type not in (FieldDescriptor.TYPE_UINT32, FieldDescriptor.TYPE_UINT64)
            low, high = (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1) if signed else (0, 2**bits - 1)
            if low <= value <= high:
                setattr(message, field.name, value)


def native_dict(message: Message) -> dict[str, Any]:
    """Read actual protobuf fields without JSON's int64-to-string conversion."""
    result = {}
    for field, value in message.ListFields():
        if field.is_repeated:
            result[field.name] = (
                [native_dict(item) for item in value]
                if field.type == FieldDescriptor.TYPE_MESSAGE
                else list(value)
            )
        elif field.type == FieldDescriptor.TYPE_MESSAGE:
            result[field.name] = native_dict(value)
        else:
            result[field.name] = value
    return result


def differences(actual: Any, wanted: Any, path: list | None = None) -> list:
    """Presence-sensitive structural corrections; preserve arbitrary JSON numerics."""
    path = [] if path is None else path
    if isinstance(actual, dict) and isinstance(wanted, dict):
        ops = [["del", [*path, key]] for key in actual if key not in wanted]
        for key, value in wanted.items():
            if key not in actual:
                ops.append(["set", [*path, key], value])
            else:
                ops.extend(differences(actual[key], value, [*path, key]))
        return ops
    if isinstance(actual, list) and isinstance(wanted, list) and len(actual) == len(wanted):
        return [
            op
            for i, (left, right) in enumerate(zip(actual, wanted, strict=True))
            for op in differences(left, right, [*path, i])
        ]
    return [] if json_bytes(actual) == json_bytes(wanted) else [["set", path, wanted]]


def restore(actual: Any, ops: list) -> Any:
    """Apply serialized corrections to a freshly parsed native projection."""
    for op in ops:
        action, path = op[:2]
        if not path:
            actual = copy.deepcopy(op[2])
            continue
        parent = actual
        for key in path[:-1]:
            parent = parent[key]
        if action == "del":
            del parent[path[-1]]
        else:
            parent[path[-1]] = copy.deepcopy(op[2])
    return actual


def template_parts(movement: dict) -> tuple[dict, dict]:
    """Factor stable structure, retaining every unknown field and presence bit."""
    template = copy.deepcopy(movement)
    dynamic = {}
    for key in ("dataHora", "orgaoJulgador"):
        if key in template:
            dynamic[key] = template.pop(key)
    complements = template.get("complementosTabelados")
    values = []
    if isinstance(complements, list):
        for comp in complements:
            if isinstance(comp, dict):
                values.append(comp.pop("valor", None))
            else:
                values.append(None)
    dynamic["valores_complementos"] = values
    return template, dynamic


def make_catalog(collections: dict[str, list[dict]]) -> tuple[list[dict], bytes]:
    templates = {}
    for docs in collections.values():
        for doc in docs:
            source = doc.get("_source")
            movements = source.get("movimentos") if isinstance(source, dict) else None
            if isinstance(movements, list):
                for movement in movements:
                    if isinstance(movement, dict):
                        template, _ = template_parts(movement)
                        templates[json_bytes(template)] = template
    ordered = [templates[key] for key in sorted(templates)]
    catalog = demo_pb2.TemplateCatalog(templates_json=[json_bytes(t) for t in ordered])
    return ordered, catalog.SerializeToString(deterministic=True)


def read_catalog(payload: bytes) -> list[dict]:
    catalog = demo_pb2.TemplateCatalog.FromString(payload)
    return [json.loads(value) for value in catalog.templates_json]


def projection(doc: dict) -> dict:
    source = doc.get("_source")
    result = dict(source) if isinstance(source, dict) else {}
    result.update(index_origem=doc.get("_index"), id_origem=doc.get("_id"))
    if "@timestamp" in result:
        result["timestamp"] = result.pop("@timestamp")
    sort = doc.get("sort")
    if isinstance(sort, list) and sort:
        result["sort_epoch"] = sort[0]
    if isinstance(doc.get("_score"), (int, float)):
        result.update(score=doc["_score"], tem_score=True)
    organ = result.get("orgaoJulgador")
    if isinstance(organ, dict):
        result["orgaoJulgador"] = {**organ, "tem_ibge": "codigoMunicipioIBGE" in organ}
    return result


def unproject(message: Message, compact: bool, templates: list[dict]) -> dict:
    return unproject_dict(native_dict(message), compact, templates)


def unproject_dict(source: dict, compact: bool, templates: list[dict]) -> dict:
    """The same inverse logical mapping for JSON and Protobuf controls."""
    result = {"_index": source.pop("index_origem", ""), "_id": source.pop("id_origem", "")}
    if "sort_epoch" in source:
        result["sort"] = [source.pop("sort_epoch")]
    if source.pop("tem_score", False):
        result["_score"] = source.pop("score", 0.0)
    if "timestamp" in source:
        source["@timestamp"] = source.pop("timestamp")
    organ = source.get("orgaoJulgador")
    if isinstance(organ, dict):
        organ.pop("tem_ibge", None)
    movements = source.get("movimentos", [])
    if compact:
        expanded = []
        for movement in movements:
            template = copy.deepcopy(templates[movement.get("tipo_id", 0)])
            template["dataHora"] = movement.get("dataHora", "")
            if "orgaoJulgador" in movement:
                template["orgaoJulgador"] = movement["orgaoJulgador"]
            values = movement.get("valores_complementos", [])
            comps = template.get("complementosTabelados")
            if isinstance(comps, list):
                for comp, value in zip(comps, values):
                    if isinstance(comp, dict):
                        comp["valor"] = value
            expanded.append(template)
        source["movimentos"] = expanded
    else:
        for movement in movements:
            movement.pop("tem_complementos", None)
    result["_source"] = source
    return result


def encode(cnj: str, docs: list[dict], compact: bool, templates: list[dict]) -> bytes:
    collection = (
        demo_pb2.CompactCollection(cnj=cnj) if compact else demo_pb2.CanonicalCollection(cnj=cnj)
    )
    ids = {json_bytes(t): i for i, t in enumerate(templates)}
    for doc in docs:
        record = collection.records.add()
        values = projection(doc)
        movements = values.get("movimentos")
        if compact and isinstance(movements, list):
            compact_movements = []
            for movement in movements:
                if isinstance(movement, dict):
                    template, dynamic = template_parts(movement)
                    compact_movements.append({"tipo_id": ids[json_bytes(template)], **dynamic})
            values["movimentos"] = compact_movements
        fill(record.document, values)
        recovered = unproject(record.document, compact, templates)
        ops = differences(recovered, doc)
        record.residual_json = json_bytes(ops) if ops else b""
    return collection.SerializeToString(deterministic=True)


def decode(payload: bytes, compact: bool, templates: list[dict]) -> tuple[str, list[dict]]:
    cls = demo_pb2.CompactCollection if compact else demo_pb2.CanonicalCollection
    collection = cls.FromString(payload)
    docs = [
        restore(
            unproject(record.document, compact, templates),
            json.loads(record.residual_json) if record.residual_json else [],
        )
        for record in collection.records
    ]
    return collection.cnj, docs
