"""Tests for scripts.synthetic_segmenter.identities — deterministic fictional identities."""

from __future__ import annotations

from scripts.synthetic_segmenter.identities import generate_identities


def test_same_seed_reproduces_identical_identities() -> None:
    a = generate_identities(123)
    b = generate_identities(123)
    assert a == b


def test_different_seeds_usually_differ() -> None:
    sets = [generate_identities(s) for s in range(10)]
    names = {s.autor.full_name for s in sets}
    assert len(names) > 1


def test_process_number_is_cnj_shaped() -> None:
    ids = generate_identities(1)
    # NNNNNNN-DD.AAAA.J.TR.OOOO -> 5 dot-separated parts: seq-dv, ano, j, tr, orgao
    parts = ids.numero_processo.split(".")
    assert len(parts) == 5
    seq_dv = parts[0].split("-")
    assert len(seq_dv) == 2
    assert len(seq_dv[0]) == 7
    assert seq_dv[0].isdigit()


def test_oab_has_uf_and_number() -> None:
    ids = generate_identities(1)
    assert ids.oab_autor.startswith("OAB/")
    assert ids.oab_reu.startswith("OAB/")


def test_identity_seed_recorded() -> None:
    ids = generate_identities(555)
    assert ids.identity_seed == 555
