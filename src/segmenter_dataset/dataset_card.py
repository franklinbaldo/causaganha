"""Human-readable dataset card generator (RFC 0012 §15 PR2 / §16.1).

RFC 0012 §15's PR2 deliverable list names a "dataset card" as a first-class
release artifact, distinct from the manifest itself: "resumo legível por
humano do manifest: escopo (tribunal/fonte/período), IAA agregado e por
categoria, known limitations, uso pretendido e não-pretendido." The
manifest already carries every one of those numbers (`ReleaseManifest`); a
card is a rendering of them for a human deciding whether to use the
release, not a new source of truth — this module reads a manifest and never
invents data it does not contain.

One field in §15's wording is not yet representable: **período** (the
release's temporal coverage). Neither `DocumentRecord` nor `SourceInfo`
carries a date field today, so there is nothing to render — the period line
is omitted rather than fabricated. Add it here once that schema gap is
closed elsewhere; do not backfill it from `created_at` (that is the release
*build* time, not the underlying documents' dates, and conflating the two
would misrepresent the corpus).
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from segmenter_dataset.schemas import ReleaseManifest


def _fmt_float(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "n/a"


def _escape_cell(value: str) -> str:
    """Escape a markdown table cell so a stray ``|`` can't corrupt the row."""
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _counts_table(counts: dict[str, int], header: str) -> list[str]:
    if not counts:
        return [f"_No {header.lower()} recorded._", ""]
    lines = [f"| {header} | Count |", "| --- | --- |"]
    lines.extend(f"| {_escape_cell(key)} | {value} |" for key, value in sorted(counts.items()))
    lines.append("")
    return lines


def _split_counts_table(counts: dict[str, int]) -> list[str]:
    lines = ["| Split | Documents |", "| --- | --- |"]
    lines.extend(f"| {role} | {counts.get(role, 0)} |" for role in ("train", "validation", "test"))
    lines.append("")
    return lines


def _iaa_section(manifest: ReleaseManifest) -> list[str]:
    quality = manifest.annotation_quality
    lines = ["## Inter-annotator agreement (IAA)", ""]
    lines.append(
        f"- **Validation macro-F1:** {_fmt_float(quality.val_iaa_span_f1)} "
        f"(95% CI lower bound: {_fmt_float(quality.val_iaa_span_f1_ci95_low)})"
    )
    lines.append(
        f"- **Test macro-F1:** {_fmt_float(quality.test_iaa_span_f1)} "
        f"(95% CI lower bound: {_fmt_float(quality.test_iaa_span_f1_ci95_low)})"
    )
    lines.append("")
    if quality.per_category_iaa:
        lines.append("| Category | IAA span F1 |")
        lines.append("| --- | --- |")
        lines.extend(
            f"| {_escape_cell(category)} | {value:.3f} |"
            for category, value in sorted(quality.per_category_iaa.items())
        )
        lines.append("")
    if quality.unreliable_eval_categories:
        unreliable = ", ".join(sorted(quality.unreliable_eval_categories))
        lines.append(
            f"**Unreliable for per-category evaluation** (below the RFC 0012 §8 floor): "
            f"{unreliable}"
        )
        lines.append("")
    return lines


def _known_limitations_section(manifest: ReleaseManifest) -> list[str]:
    lines = ["## Known limitations", ""]
    if manifest.known_limitations:
        lines.extend(
            f"- **{limitation.gate}** ({limitation.status}): {limitation.reason}"
            for limitation in manifest.known_limitations
        )
    else:
        lines.append("_None recorded._")
    lines.append("")
    return lines


def render_dataset_card(manifest: ReleaseManifest) -> str:
    """Render the RFC 0012 §15 PR2 dataset card for ``manifest`` as Markdown.

    Pure rendering — every number here is read from ``manifest``, nothing
    is recomputed or inferred. Callers that want a freshly computed number
    (e.g. re-running IAA) must do that before building the manifest, not
    after, so the card and the manifest never disagree.
    """
    lines: list[str] = [
        f"# Dataset Card: {manifest.release_id}",
        "",
        f"- **Ontology version:** {manifest.ontology_version}",
        f"- **Guideline version:** {manifest.guideline_version}",
        f"- **Source commit:** `{manifest.source_commit}`",
        f"- **Built:** {manifest.created_at}",
        f"- **CI:** {manifest.ci_provider} run `{manifest.ci_run_id}`",
        "",
        "## Scope",
        "",
    ]
    lines.extend(_counts_table(manifest.tribunals, "Tribunal"))
    lines.extend(_counts_table(manifest.document_types, "Document type"))
    lines.append("## Split sizes")
    lines.append("")
    lines.extend(_split_counts_table(manifest.counts))
    lines.extend(_iaa_section(manifest))
    lines.extend(_known_limitations_section(manifest))
    lines.append("## Intended use")
    lines.append("")
    lines.append(
        "Training and evaluating the CausaGanha decision segmenter for the tribunal(s) and "
        "document type(s) listed under Scope above. A release covering a single tribunal is "
        "described and must be used as tribunal-specific (RFC 0012 §14) — it does not license a "
        "claim of general applicability to tribunals or document types not represented here."
    )
    lines.append("")
    lines.append("## Not intended for")
    lines.append("")
    lines.append(
        "Any tribunal, document type, or time period not represented under Scope; any claim "
        "about a *model* trained on this release — dataset acceptance (RFC 0012 §16.1) is "
        "separate from, and does not imply, model-release acceptance (RFC 0012 §16.2)."
    )
    lines.append("")
    return "\n".join(lines)
