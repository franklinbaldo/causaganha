"""Tests for causaganha.processos.cnj (RFC 0014 M2) and its datajud.models reexport."""

from __future__ import annotations

from causaganha.processos.cnj import (
    CNJ_LEN,
    formatar_cnj,
    normalizar_cnj,
    so_digitos,
    validar_digito_verificador,
)


CNJ_DIGITS = "00000010220248220001"
CNJ_MASKED = "0000001-02.2024.8.22.0001"

# Sequencial 0000001, ano 2024, segmento 8 (justiça estadual), tribunal 22
# (TJRO), órgão 0001 — mesmos campos de CNJ_DIGITS, mas com o DV correto
# (56) recalculado pela fórmula da Resolução CNJ 65/2008 art. 4º (resto da
# divisão por 97 de sequencial+ano+segmento+tribunal+órgão+"00", subtraído
# de 98). CNJ_DIGITS acima tem a mesma forma de 20 dígitos mas DV "02"
# incorreto — exatamente a distinção que este validador precisa fazer.
CNJ_DV_VALIDO_DIGITS = "00000015620248220001"
CNJ_DV_VALIDO_MASKED = "0000001-56.2024.8.22.0001"


def test_so_digitos_strips_non_digits() -> None:
    assert so_digitos(CNJ_MASKED) == CNJ_DIGITS


def test_so_digitos_handles_none() -> None:
    assert so_digitos(None) == ""


def test_normalizar_cnj_accepts_unmasked() -> None:
    assert normalizar_cnj(CNJ_DIGITS) == CNJ_DIGITS


def test_normalizar_cnj_accepts_masked() -> None:
    assert normalizar_cnj(CNJ_MASKED) == CNJ_DIGITS


def test_normalizar_cnj_rejects_wrong_length() -> None:
    assert normalizar_cnj("123") == ""
    assert normalizar_cnj(CNJ_DIGITS + "9") == ""


def test_normalizar_cnj_rejects_none_and_empty() -> None:
    assert normalizar_cnj(None) == ""
    assert normalizar_cnj("") == ""


def test_formatar_cnj_masks_valid_digits() -> None:
    assert formatar_cnj(CNJ_DIGITS) == CNJ_MASKED


def test_formatar_cnj_returns_input_unchanged_when_invalid() -> None:
    assert formatar_cnj("123") == "123"


def test_cnj_len_constant() -> None:
    assert CNJ_LEN == 20


def test_validar_digito_verificador_accepts_correct_check_digit() -> None:
    assert validar_digito_verificador(CNJ_DV_VALIDO_DIGITS) is True


def test_validar_digito_verificador_accepts_masked_input() -> None:
    assert validar_digito_verificador(CNJ_DV_VALIDO_MASKED) is True


def test_validar_digito_verificador_rejects_wrong_check_digit() -> None:
    """Same 20-digit shape as CNJ_DV_VALIDO_DIGITS, but DV corrupted."""
    assert validar_digito_verificador(CNJ_DIGITS) is False


def test_validar_digito_verificador_rejects_off_by_one_check_digit() -> None:
    corrupted = CNJ_DV_VALIDO_DIGITS[:7] + "57" + CNJ_DV_VALIDO_DIGITS[9:]
    assert validar_digito_verificador(corrupted) is False


def test_validar_digito_verificador_rejects_wrong_length() -> None:
    assert validar_digito_verificador("123") is False
    assert validar_digito_verificador(CNJ_DV_VALIDO_DIGITS + "9") is False


def test_validar_digito_verificador_rejects_none_and_empty() -> None:
    assert validar_digito_verificador(None) is False
    assert validar_digito_verificador("") is False


def test_datajud_models_reexports_match_causaganha_processos_cnj() -> None:
    """`datajud.models` must not drift into its own copy of this rule."""
    from datajud import models

    assert models.normalizar_cnj is normalizar_cnj
    assert models.formatar_cnj is formatar_cnj
    assert models.so_digitos is so_digitos
    assert models.CNJ_LEN is CNJ_LEN
