"""Hybrid records: synthetic structure, real excerpt content (RFC 0011 §6.2, §14).

Composes the safeguards RFC 0011 §6.2 requires, in the order it requires
them:

1. **Origem restrita** — the excerpt must come from a TRAIN-split document
   (``split_guard.require_train_only_sources``); never val/test.
2. **Scrub de âncoras** — the excerpt goes through
   ``anchor_scrub.scrub_excerpt`` before anything else touches it, so a
   genuine anchor phrase quoted inside the real text (e.g. a cited lower
   court's "ante o exposto") can't become an unlabeled false negative.
3. **Fictionalização determinística** — ``fictionalize.fictionalize_excerpt``
   replaces structurally-detectable identifiers (RFC 0011 §7) before the
   excerpt is folded into the render.

The excerpt is then handed to ``renderer.render`` as the mérito section's
body (the only override point RFC 0011 §6.2's own example targets: "fatos/
fundamentação preenchem a camada 2") — the renderer still owns every
anchor and every offset; nothing about label placement changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.synthetic_segmenter.anchor_scrub import scrub_excerpt_with_occurrences
from scripts.synthetic_segmenter.fictionalize import fictionalize_excerpt
from scripts.synthetic_segmenter.identities import generate_identities
from scripts.synthetic_segmenter.provenance import default_provenance
from scripts.synthetic_segmenter.renderer import render
from scripts.synthetic_segmenter.split_guard import SplitAssignment, require_train_only_sources


if TYPE_CHECKING:
    from scripts.synthetic_segmenter.specs import DocumentSpec


def build_hybrid_excerpt(
    raw_excerpt: str, *, identity_seed: int, scrub_mode: str = "neutralize"
) -> tuple[str, list[dict]]:
    """Scrub anchors, then fictionalize — RFC 0011 §6.2 steps 2 and 3, in order.

    Anchor scrubbing must happen before fictionalization: scrubbing wraps
    matched surface forms verbatim (``anchor_scrub.neutralize_excerpt``),
    and running fictionalization first could rewrite a process number or
    OAB number sitting inside what would have been the wrapped span,
    changing what the anchor-detector needs to match against.

    Returns ``(text, occurrences)`` — ``occurrences`` is whatever
    ``anchor_scrub.find_anchor_occurrences`` found in the raw excerpt
    (before fictionalization), so ``build_hybrid_record`` can fold the
    actual categories found into ``hard_negative_families`` provenance
    rather than relying solely on what ``DocumentSpec`` anticipated ahead
    of time.
    """
    scrubbed, occurrences = scrub_excerpt_with_occurrences(raw_excerpt, mode=scrub_mode)
    identities = generate_identities(identity_seed)
    return fictionalize_excerpt(scrubbed, identities), occurrences


def build_hybrid_record(
    spec: DocumentSpec,
    *,
    raw_excerpt: str,
    source_doc_id: str,
    assignment: SplitAssignment,
    generator_version: str,
    corpus_release_id: str,
    scrub_mode: str = "neutralize",
) -> dict:
    """Build one ``hybrid_synthetic`` training record.

    Raises ``split_guard.SplitLeakError`` if ``source_doc_id`` isn't a
    known TRAIN document (RFC 0011 §10.4) — checked before the excerpt is
    used for anything, not after.
    """
    require_train_only_sources([source_doc_id], assignment)

    merito_body, occurrences = build_hybrid_excerpt(
        raw_excerpt, identity_seed=spec.identity_seed, scrub_mode=scrub_mode
    )
    text, labels, _identities = render(spec, merito_body_override=merito_body)

    info = default_provenance("hybrid_synthetic")
    info.update(
        {
            "source_doc_ids": [source_doc_id],
            "entities_fictionalized": True,
            "generator_version": generator_version,
            "corpus_release_id": corpus_release_id,
            "template_family": spec.template_family,
            "seed": spec.seed,
            "identity_seed": spec.identity_seed,
        }
    )

    # Union spec-anticipated hard-negative families with whatever the
    # scrub pass actually found in this specific excerpt -- the spec's
    # declared families are a prediction made before the real excerpt text
    # was known, so an excerpt with unanticipated anchor phrases (e.g.
    # scrub_mode="promote_hard_negative" left categories in place that
    # spec.hard_negative_families never listed) must not have that
    # provenance silently lost.
    found_families: set[str] = set()
    if scrub_mode == "promote_hard_negative":
        found_families = {occ["category"] for occ in occurrences}
    hard_negative_families = set(spec.hard_negative_families) | found_families
    if hard_negative_families:
        info["hard_negative_families"] = sorted(hard_negative_families)

    return {"text": text, "label": labels, "info": info}
