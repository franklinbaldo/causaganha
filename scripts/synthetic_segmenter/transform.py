"""Transformation contract for text edits that must preserve span labels.

RFC 0011 §11.1-§11.2. Any post-render mutation of a labeled record (case,
whitespace, synonym substitution, OCR noise, ...) goes through
``apply_edits``, never a raw string replace — the guarantee that
``text[start:end] == anchor`` holds only at render time (RFC 0011 §4.3);
everything after that must recompute offsets explicitly and be re-validated.

Design notes
------------
- Edits are (start, end, replacement) against the CURRENT text/labels — not
  against some earlier version. Callers building multiple edits at once
  must compute all offsets against the same snapshot.
- An edit that partially overlaps a labeled span (crosses one boundary but
  not the other) is rejected outright: RFC 0011 §11.2 requires every
  mutation to be classifiable as "outside a span" or "covering a span
  fully" — a partial overlap can't be assigned to either bucket and
  silently corrupts the label. Fully-inside and fully-covering edits are
  both allowed here; whether a specific fully-inside edit is *semantically*
  valid (i.e. the replacement is a recognized phrase-bank variant) is a
  caller concern (RFC 0011 §11.2 allowlist), not this module's.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Edit:
    """One substitution against the text passed to ``apply_edits``.

    ``start``/``end`` are character offsets into that text (end-exclusive,
    matching the label schema). ``replacement`` may be a different length
    than ``end - start`` — that's the whole point of this module.
    """

    start: int
    end: int
    replacement: str
    reason: str = ""


@dataclass(frozen=True)
class TransformationResult:
    """Output of ``apply_edits``: new text, recomputed labels, and an audit trail."""

    text: str
    labels: list[dict]
    edits: list[Edit] = field(default_factory=list)


class OverlapError(ValueError):
    """Raised when an edit partially overlaps a labeled span (RFC 0011 §11.2)."""


def _validate_edits(edits: list[Edit], text_len: int) -> None:
    ordered = sorted(edits, key=lambda e: e.start)
    prev_end = -1
    for e in ordered:
        if not (0 <= e.start < e.end <= text_len):
            msg = f"edit out of bounds: start={e.start} end={e.end} text_len={text_len}"
            raise ValueError(msg)
        if e.start < prev_end:
            msg = f"overlapping edits: an edit ends at {prev_end}, next starts at {e.start}"
            raise ValueError(msg)
        prev_end = e.end


def _classify_overlap(edit: Edit, label: dict) -> str:
    """Return 'outside', 'covers', 'inside', or 'partial' for edit vs. label span."""
    e_start, e_end = edit.start, edit.end
    l_start, l_end = label["start"], label["end"]
    if e_end <= l_start or e_start >= l_end:
        return "outside"
    if e_start <= l_start and e_end >= l_end:
        return "covers"
    if l_start <= e_start and e_end <= l_end:
        return "inside"
    return "partial"


def _position_after_edits(position: int, edits: list[Edit]) -> int:
    """Map an original-text ``position`` to its new-text position.

    Only valid for positions that don't fall strictly inside any edit's
    replaced range (i.e. label boundaries classified 'outside' every edit —
    the only case this is called for). Sums the length delta of every edit
    that lies entirely at or before ``position``.
    """
    delta = 0
    for edit in edits:
        if edit.end <= position:
            delta += len(edit.replacement) - (edit.end - edit.start)
    return position + delta


def _shift_label(label: dict, ordered_edits: list[Edit]) -> dict:
    """Recompute one label's start/end against a set of edits.

    ``ordered_edits`` must be sorted and already validated (no partial
    overlaps). Uses each edit's ORIGINAL offsets throughout — never a previously
    shifted coordinate — so multiple edits touching the same label compose
    correctly regardless of order or count (the earlier version of this
    function compared an edit's original ``end`` against an
    already-shifted local variable, which silently dropped shifts once
    more than one edit applied to the same label).
    """
    orig_start, orig_end = label["start"], label["end"]

    covering_edit = next(
        (e for e in ordered_edits if _classify_overlap(e, label) == "covers"), None
    )
    if covering_edit is not None:
        # Edits fully before the covering edit still shift its own position.
        earlier = [e for e in ordered_edits if e.end <= covering_edit.start]
        new_start = _position_after_edits(covering_edit.start, earlier)
        new_end = new_start + len(covering_edit.replacement)
        return {**label, "start": new_start, "end": new_end}

    edits_before = [e for e in ordered_edits if e.end <= orig_start]
    new_start = _position_after_edits(orig_start, edits_before)

    inside_delta = sum(
        len(e.replacement) - (e.end - e.start)
        for e in ordered_edits
        if _classify_overlap(e, label) == "inside"
    )
    new_end = orig_end + (new_start - orig_start) + inside_delta
    return {**label, "start": new_start, "end": new_end}


def apply_edits(text: str, labels: list[dict], edits: list[Edit]) -> TransformationResult:
    """Apply ``edits`` to ``text``, recomputing every label's start/end.

    Raises ``OverlapError`` if any edit partially overlaps a labeled span.
    Raises ``ValueError`` if edits are out of bounds or overlap each other.
    Does NOT run the final mechanical validator (offset bounds, category
    membership, etc.) — call ``opf_annotate.validate`` (or an equivalent
    in-process check) on the result; this function only guarantees the
    edit-map bookkeeping is correct, not that the resulting record is a
    valid training example.
    """
    _validate_edits(edits, len(text))
    ordered = sorted(edits, key=lambda e: e.start)

    for edit in ordered:
        for label in labels:
            overlap = _classify_overlap(edit, label)
            if overlap == "partial":
                msg = (
                    f"edit [{edit.start}:{edit.end}] partially overlaps label "
                    f"{label.get('category')!r} [{label['start']}:{label['end']}] — "
                    "not classifiable as outside/covers/inside (RFC 0011 §11.2)"
                )
                raise OverlapError(msg)

    new_labels: list[dict] = [_shift_label(label, ordered) for label in labels]

    new_text_parts: list[str] = []
    cursor = 0
    for edit in ordered:
        new_text_parts.append(text[cursor : edit.start])
        new_text_parts.append(edit.replacement)
        cursor = edit.end
    new_text_parts.append(text[cursor:])
    new_text = "".join(new_text_parts)

    return TransformationResult(text=new_text, labels=new_labels, edits=ordered)


def check_final_invariants(text: str, labels: list[dict]) -> list[str]:
    """Cheap structural check reused by every caller of ``apply_edits``.

    Mirrors the offset checks in ``scripts/opf_annotate.py validate`` (RFC
    0011 §4.3, §11.1) — 0 <= start < end <= len(text), text[start:end]
    non-empty, no overlapping spans. Category-membership and
    semantic-compatibility checks stay in ``validators.py`` (Phase 1, not
    Foundation) — this function only proves the edit-map didn't corrupt
    the bookkeeping.
    """
    problems: list[str] = []
    tlen = len(text)
    ordered = sorted(labels, key=lambda lab: (lab["start"], lab["end"]))
    prev_end = -1
    for label in ordered:
        start, end = label["start"], label["end"]
        cat = label.get("category", "?")
        if not (0 <= start < end <= tlen):
            problems.append(f"[{cat}] bad offsets start={start} end={end} (text_len={tlen})")
            continue
        if start < prev_end:
            problems.append(f"[{cat}] overlaps previous span (start={start} < prev_end={prev_end})")
        prev_end = max(prev_end, end)
    return problems
