"""Reconstruct document regions from OPF anchor spans (v7 ontology).

OPF produces short anchor spans. This module reconstructs full document
regions from those anchors using two schemes:

  Single-anchor: region starts at anchor, extends to next anchor or EOD.
  Start/end pair: _inicio and _fim markers bracket a discrete region.

The output is a list of Region objects suitable for downstream extraction.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.prepare_privacy_filter_dataset import (
    _PAIRED_REGION_BASES,
    SINGLE_ANCHOR_CATEGORIES,
)


MAX_SINGLE_ANCHOR_CHARS = 120

PAIRED_BASES_SET: frozenset[str] = frozenset(_PAIRED_REGION_BASES)


@dataclass(frozen=True, slots=True)
class Region:
    """A reconstructed document region from anchor spans."""

    category: str
    start: int
    end: int
    matched: bool = True


def validate_anchor_lengths(
    spans: list[dict],
    text: str,
    *,
    max_chars: int = MAX_SINGLE_ANCHOR_CHARS,
) -> list[str]:
    """Return warnings for single-anchor spans that exceed the length cap."""
    warnings: list[str] = []
    single = frozenset(SINGLE_ANCHOR_CATEGORIES)
    for sp in spans:
        cat = sp["category"]
        if cat not in single:
            continue
        length = sp["end"] - sp["start"]
        if length > max_chars:
            surface = text[sp["start"] : sp["end"]]
            preview = surface[:40] + "..." if len(surface) > 40 else surface
            warnings.append(
                f"{cat} span [{sp['start']}:{sp['end']}] is {length} chars "
                f"(max {max_chars}): {preview!r}"
            )
    return warnings


def pair_inicio_fim(
    spans: list[dict],
    text_length: int,
) -> list[Region]:
    """Match _inicio/_fim pairs; unmatched _inicio extends to EOD."""
    by_base: dict[str, list[dict]] = {}
    for sp in spans:
        cat = sp["category"]
        for base in _PAIRED_REGION_BASES:
            if cat in (f"{base}_inicio", f"{base}_fim"):
                by_base.setdefault(base, []).append(sp)
                break

    regions: list[Region] = []
    for base in _PAIRED_REGION_BASES:
        group = by_base.get(base, [])
        inicios = sorted(
            (sp for sp in group if sp["category"] == f"{base}_inicio"),
            key=lambda s: s["start"],
        )
        fins = sorted(
            (sp for sp in group if sp["category"] == f"{base}_fim"),
            key=lambda s: s["start"],
        )

        fim_idx = 0
        for ini in inicios:
            ini_end = ini["end"]
            matched_fim = None
            while fim_idx < len(fins):
                if fins[fim_idx]["start"] >= ini_end:
                    matched_fim = fins[fim_idx]
                    fim_idx += 1
                    break
                fim_idx += 1

            if matched_fim:
                regions.append(
                    Region(
                        category=base,
                        start=ini["start"],
                        end=matched_fim["end"],
                        matched=True,
                    )
                )
            else:
                regions.append(
                    Region(
                        category=base,
                        start=ini["start"],
                        end=text_length,
                        matched=False,
                    )
                )

    return sorted(regions, key=lambda r: r.start)


def reconstruct_single_anchor_regions(
    spans: list[dict],
    text_length: int,
) -> list[Region]:
    """Build tiling regions from single-anchor spans.

    Each anchor starts a region that extends to the next anchor or EOD.
    """
    single = frozenset(SINGLE_ANCHOR_CATEGORIES)
    paired_cats = frozenset(
        f"{b}_{suffix}" for b in _PAIRED_REGION_BASES for suffix in ("inicio", "fim")
    )
    all_boundaries = sorted(
        (sp for sp in spans if sp["category"] in single or sp["category"] in paired_cats),
        key=lambda s: s["start"],
    )
    regions: list[Region] = []
    for i, anchor in enumerate(all_boundaries):
        if anchor["category"] not in single:
            continue
        boundary_end = text_length
        for j in range(i + 1, len(all_boundaries)):
            boundary_end = all_boundaries[j]["start"]
            break
        regions.append(
            Region(
                category=anchor["category"],
                start=anchor["start"],
                end=boundary_end,
            )
        )
    return regions


def reconstruct_regions(
    spans: list[dict],
    text_length: int,
) -> list[Region]:
    """Reconstruct all document regions from OPF anchor spans."""
    paired = pair_inicio_fim(spans, text_length)
    single = reconstruct_single_anchor_regions(spans, text_length)
    return sorted([*paired, *single], key=lambda r: r.start)
