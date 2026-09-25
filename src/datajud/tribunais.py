"""Canonical DataJud tribunal allowlist (issue #1615).

``tribunal`` is a domain identity, not free URL/path text: every public entry
point that accepts it (``datajud_status``, ``datajud_facetas``,
``processo_estado``) eventually interpolates it into a DataJud search
endpoint path (:func:`datajud.client.search_endpoint`) or an Internet Archive
item id / bundle filename (:mod:`datajud.archive`, :mod:`datajud.state`).
None of those call sites sanitize path/query metacharacters beyond
``str.lower()`` -- an unvalidated ``tribunal`` could steer those requests to
an unexpected path segment.

The canonical set reuses :data:`causaganha.config.TRIBUNAIS` -- the project's
existing single source of truth for real-world Brazilian court sigla, "exact
siglas accepted by the DJEN caderno API" per that module's own contract --
lowercased. Reusing it avoids hand-typing a second, driftable tribunal list:
any code outside this known-good domain (path traversal, query/fragment
markers, whitespace, unicode confusables, or simply an unknown sigla) fails
closed instead of reaching a network request or filesystem/artifact name.
"""

from __future__ import annotations

from causaganha.config import TRIBUNAIS


TRIBUNAIS_DATAJUD: frozenset[str] = frozenset(codigo.lower() for codigo in TRIBUNAIS)


class TribunalInvalidoError(ValueError):
    """*tribunal* is outside the canonical DataJud allowlist."""

    def __init__(self, tribunal: str) -> None:
        self.tribunal = tribunal
        super().__init__(f"tribunal fora do conjunto canônico do DataJud: {tribunal!r}")


def validar_tribunal(tribunal: str) -> str:
    """Normalize and validate *tribunal* against the canonical allowlist.

    Returns the lowercase canonical code on success. Raises
    :class:`TribunalInvalidoError` for anything else -- this must run before
    *tribunal* reaches any network request, IA item id or bundle filename.
    """
    normalizado = tribunal.strip().lower()
    if normalizado not in TRIBUNAIS_DATAJUD:
        raise TribunalInvalidoError(tribunal)
    return normalizado
