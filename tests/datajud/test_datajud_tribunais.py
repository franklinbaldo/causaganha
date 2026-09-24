"""Tests for datajud.tribunais -- the canonical DataJud tribunal allowlist (#1615).

``tribunal`` must be treated as a domain identity, never free URL/path text.
These tests are the security gate the issue asks for: representative valid
codes pass, and every metacharacter/path-traversal/confusable shape fails
closed without ever needing a network mock -- the validator raises before
any request could be built.
"""

from __future__ import annotations

import pytest

from datajud.tribunais import TribunalInvalidoError, TRIBUNAIS_DATAJUD, validar_tribunal


@pytest.mark.parametrize("tribunal", ["tjro", "TJRO", " tjro ", "stf", "trf1", "tst"])
def test_validar_tribunal_accepts_representative_valid_codes(tribunal: str) -> None:
    assert validar_tribunal(tribunal) == tribunal.strip().lower()


@pytest.mark.parametrize(
    "tribunal",
    [
        "",
        "   ",
        "tjro/../stf",
        "../tjro",
        "tjro?x=1",
        "tjro#frag",
        "tjro%2e%2e",
        "tj ro",
        "tjro\\stf",
        "tjrо",  # Cyrillic "о" (U+043E) confusable for Latin "o"
        "does-not-exist",
    ],
)
def test_validar_tribunal_rejects_anything_outside_the_allowlist(tribunal: str) -> None:
    with pytest.raises(TribunalInvalidoError):
        validar_tribunal(tribunal)


def test_allowlist_is_lowercase_and_nonempty() -> None:
    assert TRIBUNAIS_DATAJUD
    assert all(codigo == codigo.lower() for codigo in TRIBUNAIS_DATAJUD)
