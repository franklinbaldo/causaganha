"""Tests for the DJEN-sample Technique 1 batch ingestion script (#1050).

Mirrors ``test_ingest_juris_technique1_batch.py`` for the parts this script
shares (``_build_annotation``'s call to ``ids.annotation_id``, the dangling
``_inicio`` heuristic it reuses unmodified), plus end-to-end coverage of
what's actually new here: deriving ``tribunal``/``document_type`` from each
candidate's own metadata instead of hardcoding TJRO, and skipping a
``tipoDocumento`` the v7/v8 guideline has no anchor expectations for.
"""

from __future__ import annotations

import json

from conftest import make_document
from segmenter_dataset.schemas import Label
from segmenter_dataset.store import SegmenterDatasetStore

from scripts import ingest_djen_sample_technique1_batch as module


def test_build_annotation_produces_a_valid_annotation_record() -> None:
    document = make_document()
    labels = [Label(start=0, end=9, category="cabecalho_inicio")]

    annotation = module._build_annotation(
        document,
        labels,
        allowed_unmatched={},
        covered_categories=("cabecalho_inicio",),
        completed_at="2026-09-16T00:00:00Z",
    )

    assert annotation.annotation_id.startswith("ann_")
    assert annotation.document_id == document.document_id
    assert annotation.annotator_id == module.ANNOTATOR_ID


_LABEL_SPACE = frozenset(
    {
        "dispositivo_abertura",
        "resultado",
        "ref_processual",
        "valor_condenacao",
        "fundamentacao_legal",
    }
)


def _write_candidate(tmp_path, *, key: str, tribunal: str, tipo_documento: str, text: str) -> None:
    candidates_path = tmp_path / "candidates.json"
    existing = []
    if candidates_path.exists():
        existing = json.loads(candidates_path.read_text(encoding="utf-8"))
    existing.append(
        {
            "id_documento": key,
            "tribunal": tribunal,
            "tipoDocumento": tipo_documento,
            "nomeOrgao": "1ª Vara Cível",
            "nomeClasse": "PROCEDIMENTO COMUM",
            "source_item": f"djen-{tribunal.lower()}-2026",
            "source_zip": "djen-2026-01-01-X.zip",
            "source_json": f"{key}.json",
            "sha256": "deadbeef",
            "texto_limpo": text,
        }
    )
    candidates_path.write_text(json.dumps(existing), encoding="utf-8")


def _write_tagged(tmp_path, *, key: str, tagged_text: str) -> None:
    tagged_dir = tmp_path / "tagged"
    tagged_dir.mkdir(exist_ok=True)
    (tagged_dir / f"{key}.txt").write_text(tagged_text, encoding="utf-8")


_SENTENCA_TEXT = (
    "Relatado o feito, fundamento e decido. JULGO PROCEDENTE o pedido. Publique-se. Intimem-se."
)
_SENTENCA_TAGGED = (
    "Relatado o feito, fundamento e decido. "
    "<dispositivo_abertura>JULGO PROCEDENTE</dispositivo_abertura> o pedido. "
    "Publique-se. Intimem-se."
)


def test_ingest_maps_sentenca_document_type_and_writes_document(tmp_path) -> None:
    _write_candidate(
        tmp_path, key="doc1", tribunal="TJMT", tipo_documento="Sentença", text=_SENTENCA_TEXT
    )
    _write_tagged(tmp_path, key="doc1", tagged_text=_SENTENCA_TAGGED)

    ingested, skipped = module.ingest(
        tmp_path / "candidates.json",
        tmp_path / "tagged",
        tmp_path / "store",
        _LABEL_SPACE,
        completed_at="2026-09-16T00:00:00Z",
    )

    assert skipped == {}
    assert len(ingested) == 1

    store = SegmenterDatasetStore(tmp_path / "store")
    (document,) = store.list_documents()
    assert document.source.tribunal == "TJMT"
    assert document.source.document_type == "sentenca"
    assert document.source.system == module.SOURCE_SYSTEM

    (annotation,) = store.list_annotations()
    assert annotation.document_id == document.document_id


def test_ingest_maps_acordao_document_type(tmp_path) -> None:
    text = (
        "Vistos, relatados e discutidos os autos. "
        "ACORDAM os Desembargadores negar provimento ao recurso. Publique-se."
    )
    tagged = (
        "Vistos, relatados e discutidos os autos. "
        "<resultado>ACORDAM os Desembargadores negar provimento ao recurso.</resultado> "
        "Publique-se."
    )
    _write_candidate(tmp_path, key="doc2", tribunal="TRF5", tipo_documento="Acórdão", text=text)
    _write_tagged(tmp_path, key="doc2", tagged_text=tagged)

    ingested, skipped = module.ingest(
        tmp_path / "candidates.json",
        tmp_path / "tagged",
        tmp_path / "store",
        _LABEL_SPACE,
        completed_at="2026-09-16T00:00:00Z",
    )

    assert skipped == {}
    store = SegmenterDatasetStore(tmp_path / "store")
    (document,) = store.list_documents()
    assert document.source.tribunal == "TRF5"
    assert document.source.document_type == "acordao"
    assert len(ingested) == 1


def test_ingest_skips_unsupported_document_type(tmp_path) -> None:
    _write_candidate(
        tmp_path, key="doc3", tribunal="TJCE", tipo_documento="Decisão", text="algum texto"
    )
    _write_tagged(tmp_path, key="doc3", tagged_text="algum texto")

    ingested, skipped = module.ingest(
        tmp_path / "candidates.json",
        tmp_path / "tagged",
        tmp_path / "store",
        _LABEL_SPACE,
        completed_at="2026-09-16T00:00:00Z",
    )

    assert ingested == []
    assert "unsupported tipoDocumento" in skipped["doc3"]


def test_ingest_skips_verbatim_fidelity_mismatch(tmp_path) -> None:
    _write_candidate(
        tmp_path, key="doc4", tribunal="TJPA", tipo_documento="Sentença", text=_SENTENCA_TEXT
    )
    # tagged reproduction drops a word -- reconstructed text won't match source.
    _write_tagged(
        tmp_path,
        key="doc4",
        tagged_text="<cabecalho_inicio>CABEÇALHO</cabecalho_inicio> fatos. Publique-se.",
    )

    ingested, skipped = module.ingest(
        tmp_path / "candidates.json",
        tmp_path / "tagged",
        tmp_path / "store",
        _LABEL_SPACE,
        completed_at="2026-09-16T00:00:00Z",
    )

    assert ingested == []
    assert "verbatim-fidelity mismatch" in skipped["doc4"]


def test_ingest_reports_tagged_file_with_no_matching_candidate(tmp_path) -> None:
    (tmp_path / "candidates.json").write_text("[]", encoding="utf-8")
    _write_tagged(tmp_path, key="ghost", tagged_text="texto qualquer")

    ingested, skipped = module.ingest(
        tmp_path / "candidates.json",
        tmp_path / "tagged",
        tmp_path / "store",
        _LABEL_SPACE,
        completed_at="2026-09-16T00:00:00Z",
    )

    assert ingested == []
    assert skipped["ghost"] == "no matching candidate metadata"
