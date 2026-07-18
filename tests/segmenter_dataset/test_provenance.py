from __future__ import annotations

from segmenter_dataset.provenance import extract_normalized_process_number, normalize_cnj


def test_normalize_cnj_strips_mask() -> None:
    assert normalize_cnj("7007824-46.2021.8.22.0007") == "70078244620218220007"


def test_normalize_cnj_rejects_wrong_length() -> None:
    assert normalize_cnj("123-45") is None


def test_extract_normalized_process_number_from_real_juris_header() -> None:
    """Verbatim excerpt of a real TJRO sentença — confirms the regex matches production text.

    Source: doc_020451850468f609103c41689fd50742 on the
    segmenter-pr2-corpus-ingestion branch, not a hand-written fixture format.
    """
    text = (
        "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA Tribunal de Justiça de Rondônia "
        "Cacoal - 4ª Vara Cível Avenida Cuiabá, nº 2025, Bairro Centro, "
        "CEP 76963-731, Cacoal, - cpecacoal@tjro.jus.br - Processo n.: "
        "7007824-46.2021.8.22.0007 Classe: Procedimento Comum Cível Assunto: "
        "Auxílio-Doença Previdenciário AUTOR: EDILZA LUZIA TONIATO PERIS..."
    )
    assert (
        extract_normalized_process_number(source_uri="ia://item/x", text=text)
        == "70078244620218220007"
    )


def test_extract_normalized_process_number_prefers_source_uri() -> None:
    text = "corpo do documento sem numero de processo algum aqui"
    uri = "ia://item/7000585-10.2020.8.22.0012"
    assert extract_normalized_process_number(source_uri=uri, text=text) == "70005851020208220012"


def test_extract_normalized_process_number_returns_none_when_absent() -> None:
    assert (
        extract_normalized_process_number(source_uri="ia://item/x", text="sem numero aqui") is None
    )


def test_extract_normalized_process_number_ignores_later_jurisprudence_citation() -> None:
    """Guards a real false-positive found auditing the segmenter-pr2-corpus-ingestion branch.

    Two unrelated real TJRO sentenças (doc_c2c6acba8c697497dfdb97cf7e3973ba and
    doc_ccb2ce4c263ef670e30458a9715f21fa) both cite the SAME third-party
    precedent case number deep in their body text ("Cito, ainda, trecho do
    acórdão lançado no processo n. 7000355-02.2019.8.22.0012..."). Naive "any
    CNJ-shaped number anywhere in the text" extraction would incorrectly union
    these two unrelated documents via that shared citation. Taking only the
    first match (the document's own header, which always precedes any
    body-text citation in this corpus) avoids it.
    """
    header = (
        "PODER JUDICIÁRIO DO ESTADO DE RONDÔNIA ... AUTOS : "
        "7000585-10.2020.8.22.0012 Classe Procedimento Comum Cível ..."
    )
    citation = (
        "Cito, ainda, trecho do acórdão lançado no processo n. "
        "7000355-02.2019.8.22.0012, de relatoria de ARLEN JOSE SILVA DE SOUZA, "
        "julgado em 23 de outubro de 2019."
    )
    text = f"{header} corpo da decisão. {citation}"
    assert (
        extract_normalized_process_number(source_uri="ia://item/x", text=text)
        == "70005851020208220012"
    )
