"""Process-number extraction for RFC 0012 §10 grouping keys.

``GroupingKeys.from_document`` (:mod:`segmenter_dataset.splits`) needs a real
``normalized_process_number`` to make union-find grouping fire on documents
that belong to the same processo but aren't near-duplicates of each other
(the PR #838 review's finding #1 — without this, only exact-content-hash and
>=0.9 near-dup-ratio unions ever fired in practice). JURIS/DJEN decision text
routinely states the process number verbatim (e.g. "Número do processo:
7003365-26.2025.8.22.0018"), so a regex extraction over the document's own
text/URI is enough to make the grouping key real today, without waiting on a
future ingestion pipeline to populate structured metadata.

The 20-digit validation rule mirrors ``scripts/reconcile_processos.py``'s
``normalizar_cnj``/``formatar_cnj`` (same CNJ format), reimplemented here
rather than imported — ``scripts/`` is a standalone operational script, not a
package dependency of ``segmenter_dataset``.
"""

from __future__ import annotations

import re


# RFC 0012 §8's CNJ number identity — 20 digits (7 sequential + 2 check + 4
# year + 1 segment + 2 court + 4 origin).
_CNJ_DIGIT_COUNT = 20

# NNNNNNN-DD.AAAA.J.TR.OOOO — the masked CNJ format as it appears verbatim in
# decision text and source URIs.
_CNJ_MASKED_RE = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}")

# A bare run of exactly 20 digits, not part of a longer digit run — cheaper
# to trust in a source_uri (a system-generated string) than in free text,
# where long unrelated digit runs (document IDs, dates) are common.
_CNJ_BARE_DIGITS_RE = re.compile(r"(?<!\d)\d{20}(?!\d)")


def normalize_cnj(raw: str) -> str | None:
    """Strip formatting from a CNJ number; ``None`` unless exactly 20 digits remain."""
    digits = re.sub(r"\D", "", raw)
    return digits if len(digits) == _CNJ_DIGIT_COUNT else None


def extract_normalized_process_number(*, source_uri: str, text: str) -> str | None:
    """Find a CNJ process number embedded in a document's URI or body text.

    Tries the masked format in ``source_uri`` first (cheapest, least
    ambiguous), then in ``text``, then falls back to a bare 20-digit run in
    ``source_uri`` only — free text is too likely to contain an unrelated
    20-digit sequence for that fallback to be safe there. Returns ``None``
    if no recognizable CNJ number is found anywhere.
    """
    for haystack in (source_uri, text):
        masked = _CNJ_MASKED_RE.search(haystack)
        if masked is not None:
            normalized = normalize_cnj(masked.group())
            if normalized is not None:
                return normalized

    bare = _CNJ_BARE_DIGITS_RE.search(source_uri)
    return bare.group() if bare is not None else None
