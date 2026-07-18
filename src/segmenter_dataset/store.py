r"""Filesystem layout for the segmenter dataset lifecycle (RFC 0012 §8).

```text
data/segmenter/
  documents/<document_id>.xml
  annotations/<document_id>/<annotation_id>.xml
  reviews/<document_id>/<review_id>.xml
  dataset-releases/<release-id>/manifest.csv
  dataset-releases/<release-id>/split_manifest.csv
  dataset-releases/<release-id>/checksums.sha256
```

Documents/annotations/reviews are one file per record, **inline-tagged XML**:
each label is a real XML element wrapping its own span text —
``<cabecalho_inicio>PODER JUDICIÁRIO</cabecalho_inicio>`` — rather than a
separate ``{category, start, end}`` triple pointing at an offset range. A
record's ``start``/``end`` are never stored; they're recomputed by walking the
parsed tree and tracking a running character offset. This makes an entire bug
class structurally impossible — offset drift from an edit that touches the
text but not the labels — since the position *is* the tag placement, and it
makes a record trivially human-auditable (open the file, read the tagged
document).

**Start/end pair categories nest, using XML's own open/close structure —
not a naming convention.** A flat ``<relatorio_inicio>``/``<relatorio_fim>``
pair is two unrelated tag names that happen to share a prefix; XML already
has a native way to say "these two things bound one region" — nesting. So a
matched pair renders as ``<relatorio><inicio>...</inicio>...<fim>...</fim
></relatorio>``: one wrapper element named after the category base, with
generic ``<inicio>``/``<fim>`` children reused across every pair category
(never encoded in the tag name itself). An unmatched pair (no closing cue
in the source) still gets a wrapper, just with a single child. Anything
else that falls inside the region — another category's anchor, like
``ref_processual`` sitting inside a document's ``cabecalho`` — becomes a
further nested child, found generically by interval containment, not by
any hardcoded knowledge of which categories can contain which. A single-
anchor category (no ``_inicio``/``_fim`` pairing) stays a flat leaf tag
named after itself, exactly as before — there's no region to express.

The trainable ``Label.category`` strings this reconstructs to
(``"relatorio_inicio"``, ``"relatorio_fim"``, ...) are unaffected — this is
a storage/serialization concern only. Reading is fully backward compatible
with the older flat format for free: a leaf tag whose name isn't literally
``inicio``/``fim`` is read as *its own tag name* being the category, which
is exactly what a flat ``<relatorio_inicio>`` already was.

Two regions can't always nest: RFC 0012 §11 only forbids overlapping
*labels* (short anchors), never checked whether two *regions* (the span
from one category's own inicio to its own fim) partially overlap each
other — and empirically, 3 of 150 real documents have exactly that (an
interleaved ``custas``/``honorarios`` clause, or ``voto``/``ementa``
crossing). XML can't represent a partial overlap as nesting, so any pair
of regions found to partially overlap is demoted back to flat, unwrapped
``<relatorio_inicio>``/``<relatorio_fim>`` leaf tags — same fallback the
format used everywhere before this revision, scoped now to just the rare
case that needs it.

Release-level artifacts (``manifest.csv``, ``split_manifest.csv``) stay
canonical CSV, not XML — they're pure aggregate metadata with no text-with-spans
to tag, so inline tagging buys nothing there; see the second half of this
module. They're a wide, sparse, ``record_kind``-discriminated table each,
directly queryable with plain SQL/duckdb/ibis.

Every artifact type is content-addressed and immutable (RFC 0012 §3.1) —
writing the same ID twice with identical content is a no-op; writing the same
ID with *different* content is a bug (a hash collision, or a caller computing
the ID wrong) and raises rather than silently overwriting, which is exactly
the property §3.1 requires: "o registro original... nunca é apagado nem
reescrito". Immutability is checked by reconstructing the existing record
from its file and comparing by value (Pydantic ``==``), not by comparing raw
bytes.

This module intentionally uses the stdlib ``xml.etree.ElementTree``, not an
external XML library — round-tripping a flat sequence of non-overlapping
inline tags plus attribute-only metadata elements doesn't need more than the
stdlib gives for free (automatic entity escaping on write, automatic
unescaping on parse).
"""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

from segmenter_dataset.schemas import (
    AnnotationQuality,
    AnnotationRecord,
    AnnotatorConfig,
    DocumentRecord,
    ExtractionInfo,
    GroupingInfo,
    KnownLimitation,
    Label,
    ReleaseManifest,
    ReviewRecord,
    SourceInfo,
    SplitManifest,
)


if TYPE_CHECKING:
    from pathlib import Path


class ImmutabilityError(ValueError):
    """An attempt to write different content under an existing content-addressed ID."""


def _read_csv(path: Path, fieldnames: tuple[str, ...]) -> list[dict[str, str]]:
    """Read a release-level manifest table (see the bottom of this module — still CSV)."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is not None and tuple(reader.fieldnames) != fieldnames:
            message = f"{path}: expected columns {fieldnames}, found {tuple(reader.fieldnames)}"
            raise ValueError(message)
        return list(reader)


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_xml(path: Path) -> ET.Element | None:
    if not path.exists():
        return None
    return ET.parse(path).getroot()  # noqa: S314 -- own trusted files, not external input


def _snapshot_text_subtree(element: ET.Element) -> list[tuple[ET.Element, str | None, str | None]]:
    """Capture ``(el, el.text, el.tail)`` for ``element`` and every descendant, recursively.

    Region wrappers can now nest arbitrarily deep (a category's anchors, or
    another category's region, inside a ``<relatorio>``-style wrapper), so
    the snapshot this restores after ``ET.indent`` must cover the whole
    subtree — not just direct children, which was enough back when every
    child of ``<text>`` was a leaf.
    """
    entries: list[tuple[ET.Element, str | None, str | None]] = []

    def walk(el: ET.Element) -> None:
        entries.append((el, el.text, el.tail))
        for child in el:
            walk(child)

    walk(element)
    return entries


def _write_xml(path: Path, root: ET.Element) -> None:
    """Serialize ``root`` to ``path``, pretty-printed everywhere except inside ``<text>``.

    ``ET.indent`` treats an *empty-string* ``.text``/``.tail`` as insignificant
    whitespace and overwrites it with indentation — which silently corrupts
    offsets whenever a label starts at position 0, two labels are adjacent
    with no gap, or a nested wrapper's first child starts exactly at the
    wrapper's own start (all empty-string cases, not edge cases). The
    ``<text>`` subtree's exact text/tail values are snapshotted before
    indenting and restored after, so pretty-printing the rest of the file
    can never shift a single character inside it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text_root = root.find("text")
    # text_root's own .tail sits *after* </text>, outside its content — leave it to
    # ET.indent's normal formatting. Everything from .text inward is exact-content-critical.
    snapshot = _snapshot_text_subtree(text_root) if text_root is not None else None
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    if snapshot is not None:
        for element, text, tail in snapshot:
            element.text = text
            if element is not text_root:
                element.tail = tail
    tree.write(path, encoding="unicode", xml_declaration=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n")


_PAIR_ROLES = ("inicio", "fim")


def _pair_base_and_role(category: str) -> tuple[str, str] | None:
    """``("relatorio", "inicio")`` for ``"relatorio_inicio"``; ``None`` for a single anchor."""
    for role in _PAIR_ROLES:
        suffix = f"_{role}"
        if category.endswith(suffix):
            return category[: -len(suffix)], role
    return None


def _interval_contains(outer: tuple[int, int], inner: tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def _intervals_partially_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """True if ``a``/``b`` share range without one fully containing the other.

    XML nesting can only express containment or disjointness — a partial
    overlap between two regions (see module docstring) can't be a parent/
    child relationship, so this is the trigger for demoting both regions
    back to flat leaf tags.
    """
    if a[1] <= b[0] or b[1] <= a[0]:
        return False
    return not (_interval_contains(a, b) or _interval_contains(b, a))


def _group_by_pair_base(
    labels: list[Label],
) -> tuple[dict[str, dict[str, tuple[int, Label]]], list[tuple[int, Label]]]:
    by_base: dict[str, dict[str, tuple[int, Label]]] = {}
    singles: list[tuple[int, Label]] = []
    for index, label in enumerate(labels):
        parsed = _pair_base_and_role(label.category)
        if parsed is None:
            singles.append((index, label))
            continue
        base, role = parsed
        by_base.setdefault(base, {})[role] = (index, label)
    return by_base, singles


def _region_interval(roles: dict[str, tuple[int, Label]]) -> tuple[int, int]:
    if "inicio" in roles and "fim" in roles:
        return roles["inicio"][1].start, roles["fim"][1].end
    if "inicio" in roles:
        return roles["inicio"][1].start, roles["inicio"][1].end
    return roles["fim"][1].start, roles["fim"][1].end


def _demoted_bases(region_intervals: dict[str, tuple[int, int]]) -> set[str]:
    """Bases whose region partially overlaps another — can't nest, so fall back to flat tags."""
    demoted: set[str] = set()
    bases = list(region_intervals)
    for i in range(len(bases)):
        for j in range(i + 1, len(bases)):
            if _intervals_partially_overlap(region_intervals[bases[i]], region_intervals[bases[j]]):
                demoted.add(bases[i])
                demoted.add(bases[j])
    return demoted


def _build_render_items(labels: list[Label]) -> list[dict]:
    """Flatten ``labels`` into wrapper/leaf render items (module docstring's nesting scheme)."""
    by_base, singles = _group_by_pair_base(labels)
    region_intervals = {base: _region_interval(roles) for base, roles in by_base.items()}
    demoted = _demoted_bases(region_intervals)

    items: list[dict] = []
    for base, roles in by_base.items():
        if base in demoted:
            items.extend(
                {"start": label.start, "end": label.end, "xml_tag": label.category, "ord": index}
                for index, label in roles.values()
            )
            continue
        start, end = region_intervals[base]
        items.append({"start": start, "end": end, "xml_tag": base, "wrapper": True})
        items.extend(
            {"start": label.start, "end": label.end, "xml_tag": role, "ord": index}
            for role, (index, label) in roles.items()
        )
    items.extend(
        {"start": label.start, "end": label.end, "xml_tag": label.category, "ord": index}
        for index, label in singles
    )
    return items


def _nest_render_items(items: list[dict]) -> list[dict]:
    """Group ``items`` into a forest by interval containment.

    A wrapper sorts before an equal-span leaf child — e.g. an unmatched
    pair's single anchor, which shares its wrapper's exact interval.
    """

    def sort_key(item: dict) -> tuple[int, int, int]:
        return (item["start"], -item["end"], 0 if item.get("wrapper") else 1)

    roots: list[dict] = []
    stack: list[dict] = []
    for item in sorted(items, key=sort_key):
        item["children"] = []
        while stack and stack[-1]["end"] <= item["start"]:
            stack.pop()
        (stack[-1]["children"] if stack else roots).append(item)
        stack.append(item)
    return roots


def _render_item(item: dict, text: str) -> ET.Element:
    element = ET.Element(item["xml_tag"])
    if not item.get("wrapper"):
        element.set("ord", str(item["ord"]))
    cursor = item["start"]
    last_child: ET.Element | None = None
    for child in item["children"]:
        gap = text[cursor : child["start"]]
        if last_child is None:
            element.text = (element.text or "") + gap
        else:
            last_child.tail = (last_child.tail or "") + gap
        last_child = _render_item(child, text)
        element.append(last_child)
        cursor = child["end"]
    trailing = text[cursor : item["end"]]
    if last_child is None:
        element.text = (element.text or "") + trailing
    else:
        last_child.tail = (last_child.tail or "") + trailing
    return element


def _labels_to_text_element(tag: str, text: str, labels: list[Label]) -> ET.Element:
    """Build a ``<tag>`` element with each label inlined as a child wrapping its span.

    Start/end pairs nest under a ``<base>`` wrapper with generic
    ``<inicio>``/``<fim>`` children (module docstring); single-anchor
    categories stay flat leaves. Everything — wrapper regions, their own
    anchors, and any other label whose span falls inside a region — goes
    through one generic interval-containment pass (:func:`_nest_render_items`),
    so a category nested inside another (``ref_processual`` inside
    ``cabecalho``) needs no special-casing.

    A caller's ``labels`` list order is independently meaningful
    (``ids.annotation_id`` hashes it positionally, Pydantic list equality
    is order-sensitive) and need not be start-sorted, so every leaf carries
    its original list index as an ``ord`` attribute — :func:`_text_element_to_labels`
    restores the exact original order regardless of document position.
    """
    roots = _nest_render_items(_build_render_items(labels))
    root_item = {"start": 0, "end": len(text), "xml_tag": tag, "wrapper": True, "children": roots}
    return _render_item(root_item, text)


def _text_element_to_labels(element: ET.Element) -> tuple[str, list[Label]]:
    """Inverse of :func:`_labels_to_text_element`: recover plain text and offset labels.

    Fully backward compatible with the pre-nesting flat format: a leaf
    whose tag isn't literally ``inicio``/``fim`` is read as *its own tag
    name* being the category — exactly what a flat ``<relatorio_inicio>``
    already meant. Returned in the labels' original list order (each
    leaf's ``ord`` attribute), not document order.
    """

    def walk(el: ET.Element) -> tuple[str, list[tuple[int, Label]]]:
        chunks: list[str] = [el.text or ""]
        cursor = len(chunks[0])
        collected: list[tuple[int, Label]] = []
        for child in el:
            child_text, child_items = walk(child)
            if child.tag in _PAIR_ROLES:
                category = f"{el.tag}_{child.tag}"
                original_index = int(child.get("ord", "0"))
                collected.append(
                    (
                        original_index,
                        Label(start=cursor, end=cursor + len(child_text), category=category),
                    )
                )
            elif child_items:
                # child is itself a region wrapper — splice its already-resolved
                # labels in, shifted from child-relative to this element's cursor.
                collected.extend(
                    (
                        index,
                        Label(
                            start=label.start + cursor,
                            end=label.end + cursor,
                            category=label.category,
                        ),
                    )
                    for index, label in child_items
                )
            else:
                original_index = int(child.get("ord", "0"))
                collected.append(
                    (
                        original_index,
                        Label(start=cursor, end=cursor + len(child_text), category=child.tag),
                    )
                )
            chunks.append(child_text)
            cursor += len(child_text)
            tail = child.tail or ""
            chunks.append(tail)
            cursor += len(tail)
        return "".join(chunks), collected

    text, indexed_labels = walk(element)
    indexed_labels.sort(key=lambda pair: pair[0])
    return text, [label for _, label in indexed_labels]


def _pack_list(parent: ET.Element, tag: str, item_tag: str, items: tuple[str, ...]) -> None:
    container = ET.SubElement(parent, tag)
    for item in items:
        child = ET.SubElement(container, item_tag)
        child.text = item


def _unpack_list(parent: ET.Element, tag: str) -> tuple[str, ...]:
    container = parent.find(tag)
    if container is None:
        return ()
    return tuple(child.text or "" for child in container)


def _pack_allowed_unmatched(parent: ET.Element, allowed_unmatched: dict[str, str]) -> None:
    container = ET.SubElement(parent, "allowed_unmatched")
    for base, reason in allowed_unmatched.items():
        entry = ET.SubElement(container, "entry")
        entry.set("base", base)
        entry.set("reason", reason)


def _unpack_allowed_unmatched(parent: ET.Element) -> dict[str, str]:
    container = parent.find("allowed_unmatched")
    if container is None:
        return {}
    return {entry.get("base", ""): entry.get("reason", "") for entry in container}


def _document_to_xml(document: DocumentRecord) -> ET.Element:
    root = ET.Element("document", id=document.document_id)
    source = document.source
    ET.SubElement(
        root,
        "source",
        system=source.system,
        tribunal=source.tribunal,
        document_type=source.document_type,
        uri=source.source_uri,
        hash=source.source_hash,
    )
    ET.SubElement(
        root, "extraction", method=document.extraction.method, version=document.extraction.version
    )
    grouping = document.grouping
    grouping_attrs = {
        key: value
        for key, value in (
            ("normalized_process_number", grouping.normalized_process_number),
            ("source_process_id", grouping.source_process_id),
            ("document_family", grouping.document_family),
            ("parent_document_id", grouping.parent_document_id),
        )
        if value is not None
    }
    ET.SubElement(root, "grouping", **grouping_attrs)
    text_element = _labels_to_text_element("text", document.text, document.proposed_labels)
    root.append(text_element)
    return root


def _xml_to_document(root: ET.Element) -> DocumentRecord:
    source = root.find("source")
    extraction = root.find("extraction")
    grouping = root.find("grouping")
    text, proposed_labels = _text_element_to_labels(root.find("text"))
    return DocumentRecord(
        document_id=root.get("id", ""),
        text=text,
        proposed_labels=proposed_labels,
        source=SourceInfo(
            system=source.get("system", ""),
            tribunal=source.get("tribunal", ""),
            document_type=source.get("document_type", ""),
            source_uri=source.get("uri", ""),
            source_hash=source.get("hash", ""),
        ),
        extraction=ExtractionInfo(
            method=extraction.get("method", ""), version=extraction.get("version", "")
        ),
        grouping=GroupingInfo(
            normalized_process_number=grouping.get("normalized_process_number"),
            source_process_id=grouping.get("source_process_id"),
            document_family=grouping.get("document_family"),
            parent_document_id=grouping.get("parent_document_id"),
        ),
    )


def _annotation_to_xml(annotation: AnnotationRecord, document_text: str) -> ET.Element:
    root = ET.Element("annotation", id=annotation.annotation_id, document_id=annotation.document_id)
    config = annotation.annotator_config
    ET.SubElement(
        root,
        "annotator",
        id=annotation.annotator_id,
        model_family=config.model_family,
        guideline_version=config.guideline_version,
        seeded_with=config.seeded_with,
    )
    ontology = ET.SubElement(root, "ontology_version")
    ontology.text = annotation.ontology_version
    _pack_list(root, "covered_categories", "category", annotation.covered_categories)
    _pack_allowed_unmatched(root, annotation.allowed_unmatched)
    completed_at = ET.SubElement(root, "completed_at")
    completed_at.text = annotation.completed_at
    method = ET.SubElement(root, "annotation_method")
    method.text = annotation.annotation_method
    root.append(_labels_to_text_element("text", document_text, annotation.labels))
    return root


def _xml_to_annotation(root: ET.Element) -> AnnotationRecord:
    annotator = root.find("annotator")
    _, labels = _text_element_to_labels(root.find("text"))
    return AnnotationRecord(
        annotation_id=root.get("id", ""),
        document_id=root.get("document_id", ""),
        annotator_id=annotator.get("id", ""),
        annotator_config=AnnotatorConfig(
            model_family=annotator.get("model_family", ""),
            guideline_version=annotator.get("guideline_version", ""),
            seeded_with=annotator.get("seeded_with", ""),
        ),
        ontology_version=root.findtext("ontology_version", ""),
        covered_categories=_unpack_list(root, "covered_categories"),
        labels=labels,
        allowed_unmatched=_unpack_allowed_unmatched(root),
        completed_at=root.findtext("completed_at", ""),
        annotation_method=root.findtext("annotation_method", ""),
    )


def _review_to_xml(review: ReviewRecord, document_text: str) -> ET.Element:
    root = ET.Element("review", id=review.review_id, document_id=review.document_id)
    _pack_list(root, "input_annotations", "annotation_id", review.input_annotation_ids)
    status = ET.SubElement(root, "status")
    status.text = review.status
    _pack_allowed_unmatched(root, review.allowed_unmatched)
    _pack_list(root, "reviewers", "reviewer", review.reviewers)
    resolution = ET.SubElement(root, "resolution")
    resolution.text = review.resolution
    _pack_list(root, "notes", "note", review.notes)
    approved_at = ET.SubElement(root, "approved_at")
    approved_at.text = review.approved_at
    root.append(_labels_to_text_element("text", document_text, review.final_labels))
    return root


def _xml_to_review(root: ET.Element) -> ReviewRecord:
    _, final_labels = _text_element_to_labels(root.find("text"))
    return ReviewRecord(
        review_id=root.get("id", ""),
        document_id=root.get("document_id", ""),
        input_annotation_ids=_unpack_list(root, "input_annotations"),
        status=root.findtext("status", ""),
        final_labels=final_labels,
        allowed_unmatched=_unpack_allowed_unmatched(root),
        reviewers=_unpack_list(root, "reviewers"),
        resolution=root.findtext("resolution", ""),
        notes=_unpack_list(root, "notes"),
        approved_at=root.findtext("approved_at", ""),
    )


class SegmenterDatasetStore:
    """Read/write access to ``data/segmenter/``'s canonical artifacts (RFC 0012 §8)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.documents_dir = root / "documents"
        self.annotations_dir = root / "annotations"
        self.reviews_dir = root / "reviews"
        self.releases_dir = root / "dataset-releases"

    # -- documents ----------------------------------------------------

    def write_document(self, document: DocumentRecord) -> None:
        path = self.documents_dir / f"{document.document_id}.xml"
        existing_root = _read_xml(path)
        if existing_root is not None:
            if _xml_to_document(existing_root) != document:
                message = (
                    f"document {document.document_id!r} already exists with different "
                    "content — this should be impossible unless the ID was computed "
                    "incorrectly (RFC 0012 §3.1)"
                )
                raise ImmutabilityError(message)
            return
        _write_xml(path, _document_to_xml(document))

    def read_document(self, document_id: str) -> DocumentRecord:
        root = _read_xml(self.documents_dir / f"{document_id}.xml")
        if root is None:
            message = f"no document {document_id!r} in {self.root}"
            raise FileNotFoundError(message)
        return _xml_to_document(root)

    def list_documents(self) -> list[DocumentRecord]:
        if not self.documents_dir.exists():
            return []
        return [
            _xml_to_document(ET.parse(path).getroot())  # noqa: S314 -- own trusted files
            for path in sorted(self.documents_dir.glob("*.xml"))
        ]

    # -- annotations ----------------------------------------------------

    def write_annotation(self, annotation: AnnotationRecord) -> None:
        path = self.annotations_dir / annotation.document_id / f"{annotation.annotation_id}.xml"
        existing_root = _read_xml(path)
        if existing_root is not None:
            if _xml_to_annotation(existing_root) != annotation:
                message = (
                    f"annotation {annotation.annotation_id!r} already exists with different "
                    "content — this should be impossible unless the ID was computed "
                    "incorrectly (RFC 0012 §3.1)"
                )
                raise ImmutabilityError(message)
            return
        document_text = self.read_document(annotation.document_id).text
        _write_xml(path, _annotation_to_xml(annotation, document_text))

    def list_annotations(self, document_id: str | None = None) -> list[AnnotationRecord]:
        if not self.annotations_dir.exists():
            return []
        pattern = f"{document_id}/*.xml" if document_id else "*/*.xml"
        return [
            _xml_to_annotation(ET.parse(path).getroot())  # noqa: S314 -- own trusted files
            for path in sorted(self.annotations_dir.glob(pattern))
        ]

    # -- reviews ----------------------------------------------------

    def write_review(self, review: ReviewRecord) -> None:
        path = self.reviews_dir / review.document_id / f"{review.review_id}.xml"
        existing_root = _read_xml(path)
        if existing_root is not None:
            if _xml_to_review(existing_root) != review:
                message = (
                    f"review {review.review_id!r} already exists with different content — "
                    "this should be impossible unless the ID was computed incorrectly "
                    "(RFC 0012 §3.1)"
                )
                raise ImmutabilityError(message)
            return
        document_text = self.read_document(review.document_id).text
        _write_xml(path, _review_to_xml(review, document_text))

    def list_reviews(self, document_id: str | None = None) -> list[ReviewRecord]:
        if not self.reviews_dir.exists():
            return []
        pattern = f"{document_id}/*.xml" if document_id else "*/*.xml"
        return [
            _xml_to_review(ET.parse(path).getroot())  # noqa: S314 -- own trusted files
            for path in sorted(self.reviews_dir.glob(pattern))
        ]

    # -- releases ----------------------------------------------------

    def release_dir(self, release_id: str) -> Path:
        return self.releases_dir / release_id

    def write_release_manifest(self, manifest: ReleaseManifest) -> None:
        """Write the final release manifest. Refuses to overwrite an existing release (§12)."""
        release_dir = self.release_dir(manifest.release_id)
        if (release_dir / "manifest.csv").exists():
            message = (
                f"release {manifest.release_id!r} already exists at {release_dir} — "
                "refusing to overwrite (RFC 0012 §12)"
            )
            raise ImmutabilityError(message)
        write_release_manifest_tables(release_dir, manifest)

    def read_release_manifest(self, release_id: str) -> ReleaseManifest:
        return read_release_manifest_tables(self.release_dir(release_id))


_MANIFEST_FIELDS = (
    "record_kind",  # manifest | split_hash | document_resolution | count | tribunal
    # | document_type | per_category_iaa | unreliable_category | known_limitation
    "role",
    "ordinal",
    "key",
    "value",
    "extra",
    # -- the single "manifest" row only --
    "release_id",
    "ontology_version",
    "guideline_version",
    "source_commit",
    "dependency_lock_hash",
    "ci_provider",
    "ci_run_id",
    "split_manifest_hash",
    "iaa_seed",
    "iaa_resamples",
    "created_at",
    "val_iaa_span_f1",
    "val_iaa_span_f1_ci95_low",
    "test_iaa_span_f1",
    "test_iaa_span_f1_ci95_low",
)


def _manifest_blank() -> dict[str, object]:
    return dict.fromkeys(_MANIFEST_FIELDS, "")


def _manifest_header_row(manifest: ReleaseManifest) -> dict[str, object]:
    quality = manifest.annotation_quality
    row = _manifest_blank()
    row.update(
        record_kind="manifest",
        release_id=manifest.release_id,
        ontology_version=manifest.ontology_version,
        guideline_version=manifest.guideline_version,
        source_commit=manifest.source_commit,
        dependency_lock_hash=manifest.dependency_lock_hash,
        ci_provider=manifest.ci_provider,
        ci_run_id=manifest.ci_run_id,
        split_manifest_hash=manifest.split_manifest_hash,
        iaa_seed=manifest.iaa_seed,
        iaa_resamples=manifest.iaa_resamples,
        created_at=manifest.created_at,
        val_iaa_span_f1=_optional(quality.val_iaa_span_f1),
        val_iaa_span_f1_ci95_low=_optional(quality.val_iaa_span_f1_ci95_low),
        test_iaa_span_f1=_optional(quality.test_iaa_span_f1),
        test_iaa_span_f1_ci95_low=_optional(quality.test_iaa_span_f1_ci95_low),
    )
    return row


def _manifest_kv_rows(
    record_kind: str, items: dict[str, object], *, role: str | None = None
) -> list[dict]:
    rows = []
    for key, value in items.items():
        row = _manifest_blank()
        row.update(record_kind=record_kind, key=key, value=value)
        if role is not None:
            row["role"] = role
        rows.append(row)
    return rows


def _manifest_document_resolution_rows(manifest: ReleaseManifest) -> list[dict]:
    return [
        row
        for role, resolutions in manifest.document_resolutions.items()
        for row in _manifest_kv_rows("document_resolution", resolutions, role=role)
    ]


def _manifest_unreliable_category_rows(manifest: ReleaseManifest) -> list[dict]:
    rows = []
    for ordinal, category in enumerate(manifest.annotation_quality.unreliable_eval_categories):
        row = _manifest_blank()
        row.update(record_kind="unreliable_category", ordinal=ordinal, key=category)
        rows.append(row)
    return rows


def _manifest_known_limitation_rows(manifest: ReleaseManifest) -> list[dict]:
    rows = []
    for item in manifest.known_limitations:
        row = _manifest_blank()
        row.update(
            record_kind="known_limitation", key=item.gate, value=item.status, extra=item.reason
        )
        rows.append(row)
    return rows


def _manifest_split_hash_rows(manifest: ReleaseManifest) -> list[dict]:
    rows = []
    for role, value in manifest.split_hashes.items():
        row = _manifest_blank()
        row.update(record_kind="split_hash", role=role, value=value)
        rows.append(row)
    return rows


def _manifest_count_rows(manifest: ReleaseManifest) -> list[dict]:
    rows = []
    for role, count in manifest.counts.items():
        row = _manifest_blank()
        row.update(record_kind="count", role=role, value=count)
        rows.append(row)
    return rows


def write_release_manifest_tables(release_dir: Path, manifest: ReleaseManifest) -> None:
    """Write a :class:`ReleaseManifest` as a single canonical CSV under ``release_dir``."""
    quality = manifest.annotation_quality
    rows = [
        _manifest_header_row(manifest),
        *_manifest_split_hash_rows(manifest),
        *_manifest_document_resolution_rows(manifest),
        *_manifest_count_rows(manifest),
        *_manifest_kv_rows("tribunal", manifest.tribunals),
        *_manifest_kv_rows("document_type", manifest.document_types),
        *_manifest_kv_rows("per_category_iaa", quality.per_category_iaa),
        *_manifest_unreliable_category_rows(manifest),
        *_manifest_known_limitation_rows(manifest),
    ]
    _write_csv(release_dir / "manifest.csv", _MANIFEST_FIELDS, rows)


def read_release_manifest_tables(release_dir: Path) -> ReleaseManifest:
    """Read a :class:`ReleaseManifest` back from ``release_dir``'s canonical CSV."""
    rows = _read_csv(release_dir / "manifest.csv", _MANIFEST_FIELDS)
    header = next((row for row in rows if row["record_kind"] == "manifest"), None)
    if header is None:
        message = f"no release manifest at {release_dir}"
        raise FileNotFoundError(message)

    split_hashes = {row["role"]: row["value"] for row in rows if row["record_kind"] == "split_hash"}

    document_resolutions: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["record_kind"] == "document_resolution":
            document_resolutions.setdefault(row["role"], {})[row["key"]] = row["value"]

    counts = {row["role"]: int(row["value"]) for row in rows if row["record_kind"] == "count"}
    tribunals = {row["key"]: int(row["value"]) for row in rows if row["record_kind"] == "tribunal"}
    document_types = {
        row["key"]: int(row["value"]) for row in rows if row["record_kind"] == "document_type"
    }
    per_category_iaa = {
        row["key"]: float(row["value"]) for row in rows if row["record_kind"] == "per_category_iaa"
    }
    unreliable_rows = sorted(
        (row for row in rows if row["record_kind"] == "unreliable_category"),
        key=lambda row: int(row["ordinal"]),
    )
    unreliable_eval_categories = tuple(row["key"] for row in unreliable_rows)
    known_limitations = tuple(
        KnownLimitation(gate=row["key"], status=row["value"], reason=row["extra"])
        for row in rows
        if row["record_kind"] == "known_limitation"
    )

    return ReleaseManifest(
        release_id=header["release_id"],
        ontology_version=header["ontology_version"],
        guideline_version=header["guideline_version"],
        source_commit=header["source_commit"],
        dependency_lock_hash=header["dependency_lock_hash"],
        ci_provider=header["ci_provider"],
        ci_run_id=header["ci_run_id"],
        split_manifest_hash=header["split_manifest_hash"],
        split_hashes=split_hashes,
        document_resolutions=document_resolutions,
        counts=counts,
        tribunals=tribunals,
        document_types=document_types,
        annotation_quality=AnnotationQuality(
            val_iaa_span_f1=_optional_float(header["val_iaa_span_f1"]),
            val_iaa_span_f1_ci95_low=_optional_float(header["val_iaa_span_f1_ci95_low"]),
            test_iaa_span_f1=_optional_float(header["test_iaa_span_f1"]),
            test_iaa_span_f1_ci95_low=_optional_float(header["test_iaa_span_f1_ci95_low"]),
            per_category_iaa=per_category_iaa,
            unreliable_eval_categories=unreliable_eval_categories,
        ),
        iaa_seed=int(header["iaa_seed"]),
        iaa_resamples=int(header["iaa_resamples"]),
        known_limitations=known_limitations,
        created_at=header["created_at"],
    )


_SPLIT_MANIFEST_FIELDS = (
    "record_kind",  # manifest | id | group
    "role",  # train | val | test (id rows)
    "ordinal",
    "key",  # group_id (group rows)
    "value",  # document_id (id and group rows)
    "seed",
    "train_ratio",
    "val_ratio",
    "near_duplicate_threshold",
)


def write_split_manifest(release_dir: Path, manifest: SplitManifest) -> None:
    """Write a :class:`SplitManifest` as a single canonical CSV under ``release_dir``."""

    def blank() -> dict[str, object]:
        return dict.fromkeys(_SPLIT_MANIFEST_FIELDS, "")

    rows: list[dict[str, object]] = []

    header = blank()
    header.update(
        record_kind="manifest",
        seed=manifest.seed,
        train_ratio=manifest.train_ratio,
        val_ratio=manifest.val_ratio,
        near_duplicate_threshold=manifest.near_duplicate_threshold,
    )
    rows.append(header)

    for role, ids in (
        ("train", manifest.train_ids),
        ("val", manifest.val_ids),
        ("test", manifest.test_ids),
    ):
        for ordinal, document_id in enumerate(ids):
            row = blank()
            row.update(record_kind="id", role=role, ordinal=ordinal, value=document_id)
            rows.append(row)

    for group_id, members in manifest.groups.items():
        for ordinal, document_id in enumerate(members):
            row = blank()
            row.update(record_kind="group", key=group_id, ordinal=ordinal, value=document_id)
            rows.append(row)

    _write_csv(release_dir / "split_manifest.csv", _SPLIT_MANIFEST_FIELDS, rows)


def read_split_manifest(release_dir: Path) -> SplitManifest:
    """Read a :class:`SplitManifest` back from ``release_dir``'s canonical CSV."""
    rows = _read_csv(release_dir / "split_manifest.csv", _SPLIT_MANIFEST_FIELDS)
    header = next((row for row in rows if row["record_kind"] == "manifest"), None)
    if header is None:
        message = f"no split manifest at {release_dir}"
        raise FileNotFoundError(message)

    ids_by_role: dict[str, list[tuple[int, str]]] = {"train": [], "val": [], "test": []}
    for row in rows:
        if row["record_kind"] == "id":
            ids_by_role[row["role"]].append((int(row["ordinal"]), row["value"]))
    for role_ids in ids_by_role.values():
        role_ids.sort()

    groups: dict[str, list[tuple[int, str]]] = {}
    for row in rows:
        if row["record_kind"] == "group":
            groups.setdefault(row["key"], []).append((int(row["ordinal"]), row["value"]))
    for members in groups.values():
        members.sort()

    return SplitManifest(
        train_ids=tuple(doc_id for _, doc_id in ids_by_role["train"]),
        val_ids=tuple(doc_id for _, doc_id in ids_by_role["val"]),
        test_ids=tuple(doc_id for _, doc_id in ids_by_role["test"]),
        seed=int(header["seed"]),
        train_ratio=float(header["train_ratio"]),
        val_ratio=float(header["val_ratio"]),
        near_duplicate_threshold=float(header["near_duplicate_threshold"]),
        groups={
            group_id: tuple(doc_id for _, doc_id in members) for group_id, members in groups.items()
        },
    )


def _optional(value: float | None) -> str:
    return "" if value is None else str(value)


def _optional_float(value: str) -> float | None:
    return float(value) if value else None
