"""Deterministic fictionalization of structural identifiers in real excerpts.

RFC 0011 §7 (hybrid records): a real excerpt folded into a hybrid record
must have its selected identities replaced deterministically, while
leaving legal citations, anchor phrases, labeled monetary values, labeled
process references, and tribunal/style metadata untouched — "não
substituir indiscriminadamente".

**Scope, honestly stated**: this module only replaces *structurally
detectable* identifiers — CNJ-shaped process numbers and OAB numbers,
found by regex, exactly like ``identities.py`` generates them. It is
**not** an NER system and does not detect or replace free-form party/
lawyer/judge names in prose — that would require a named-entity model, a
different tier of infrastructure than Phase 2 needs (RFC 0011 §7's
anti-memorization rationale is a dataset-quality choice, not a legal
requirement per docs/GOVERNANCE.md, so this partial scope is an accepted
trade-off, not a gap to silently paper over).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from scripts.synthetic_segmenter.identities import IdentitySet


_PROCESS_NUMBER_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
_OAB_RE = re.compile(r"\bOAB/[A-Z]{2}\s*\d{1,6}\b")


def fictionalize_excerpt(text: str, identities: IdentitySet) -> str:
    """Replace every CNJ-shaped process number and OAB number in ``text``.

    Deterministic in ``identities`` — the same ``IdentitySet`` always
    produces the same substitution. Legal citations ("art. 927 do CPC"),
    monetary values, and free-form names are left untouched (see module
    docstring for scope). Distinct OAB occurrences alternate between
    ``identities.oab_autor``/``oab_reu`` rather than collapsing every
    lawyer mentioned to the same fictional number.
    """
    text = _PROCESS_NUMBER_RE.sub(identities.numero_processo, text)

    oab_pool = (identities.oab_autor, identities.oab_reu)
    counter = {"n": 0}

    def _next_oab(_match: re.Match[str]) -> str:
        value = oab_pool[counter["n"] % len(oab_pool)]
        counter["n"] += 1
        return value

    return _OAB_RE.sub(_next_oab, text)
