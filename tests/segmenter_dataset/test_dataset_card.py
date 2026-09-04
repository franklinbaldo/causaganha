from __future__ import annotations

from segmenter_dataset.dataset_card import render_dataset_card
from segmenter_dataset.schemas import AnnotationQuality, KnownLimitation, ReleaseManifest


SOURCE_COMMIT = "a" * 40
LOCK_HASH = "b" * 64
SPLIT_HASH = "c" * 64


def _manifest(**overrides: object) -> ReleaseManifest:
    defaults = {
        "release_id": "segmenter-silver-v8.1",
        "ontology_version": "segmenter-ontology-v8.0.0",
        "guideline_version": "v7.3",
        "source_commit": SOURCE_COMMIT,
        "dependency_lock_hash": LOCK_HASH,
        "ci_provider": "github-actions",
        "ci_run_id": "123",
        "split_manifest_hash": SPLIT_HASH,
        "split_hashes": {"train": SPLIT_HASH, "validation": SPLIT_HASH, "test": SPLIT_HASH},
        "document_resolutions": {},
        "counts": {"train": 150, "validation": 30, "test": 30},
        "tribunals": {"tjro": 210},
        "document_types": {"acordao": 210},
        "annotation_quality": AnnotationQuality(
            val_iaa_span_f1=0.82,
            val_iaa_span_f1_ci95_low=0.78,
            test_iaa_span_f1=0.80,
            test_iaa_span_f1_ci95_low=0.76,
            per_category_iaa={"resultado": 0.9, "cabecalho_inicio": 0.85},
            unreliable_eval_categories=("valor_condenacao",),
        ),
        "iaa_seed": 1,
        "iaa_resamples": 1000,
        "known_limitations": (),
        "created_at": "2026-07-18T00:00:00Z",
    }
    defaults.update(overrides)
    return ReleaseManifest(**defaults)


def test_card_includes_release_id_and_versions() -> None:
    card = render_dataset_card(_manifest())

    assert "# Dataset Card: segmenter-silver-v8.1" in card
    assert "segmenter-ontology-v8.0.0" in card
    assert "v7.3" in card


def test_card_includes_scope_tables() -> None:
    card = render_dataset_card(_manifest())

    assert "| tjro | 210 |" in card
    assert "| acordao | 210 |" in card


def test_card_includes_split_sizes() -> None:
    card = render_dataset_card(_manifest())

    assert "| train | 150 |" in card
    assert "| validation | 30 |" in card
    assert "| test | 30 |" in card


def test_card_includes_iaa_aggregate_and_per_category() -> None:
    card = render_dataset_card(_manifest())

    assert "0.820" in card  # val macro-F1
    assert "0.780" in card  # val CI low
    assert "| resultado | 0.900 |" in card
    assert "valor_condenacao" in card
    assert "Unreliable for per-category evaluation" in card


def test_card_reports_no_limitations_when_none_recorded() -> None:
    card = render_dataset_card(_manifest())

    assert "_None recorded._" in card


def test_card_lists_known_limitations() -> None:
    manifest = _manifest(
        known_limitations=(
            KnownLimitation(gate="iaa_per_category_floor", reason="low support for X"),
        )
    )

    card = render_dataset_card(manifest)

    assert "iaa_per_category_floor" in card
    assert "low support for X" in card


def test_card_never_fabricates_a_temporal_period_line() -> None:
    """RFC 0012 §15 mentions 'período' in scope, but no schema field carries it yet --
    the card must not invent one (e.g. from created_at, which is build time not corpus time).
    """
    card = render_dataset_card(_manifest())

    assert "período" not in card.lower()
    assert "**period" not in card.lower()


def test_card_does_not_fabricate_iaa_numbers_when_absent() -> None:
    manifest = _manifest(
        annotation_quality=AnnotationQuality(),
    )

    card = render_dataset_card(manifest)

    assert "n/a" in card


def test_card_escapes_pipe_in_tribunal_name_so_table_stays_well_formed() -> None:
    manifest = _manifest(tribunals={"TJRO|fake": 1})

    card = render_dataset_card(manifest)

    assert "| TJRO\\|fake | 1 |" in card
    # every table row must have exactly the 3 unescaped pipes a 2-column row needs
    row = next(line for line in card.splitlines() if "TJRO" in line)
    assert row.count("|") - row.count("\\|") == 3


def test_card_escapes_pipe_in_iaa_category_name() -> None:
    manifest = _manifest(
        annotation_quality=AnnotationQuality(per_category_iaa={"weird|category": 0.5})
    )

    card = render_dataset_card(manifest)

    assert "| weird\\|category | 0.500 |" in card


def test_card_reports_no_tribunals_when_scope_is_empty() -> None:
    manifest = _manifest(tribunals={}, document_types={})

    card = render_dataset_card(manifest)

    assert "_No tribunal recorded._" in card
    assert "_No document type recorded._" in card


def test_card_reports_no_category_counts_when_none_recorded() -> None:
    card = render_dataset_card(_manifest())

    assert "_No category counts recorded._" in card


def test_card_includes_category_support_table() -> None:
    manifest = _manifest(
        category_counts={
            "train:resultado": 12,
            "val:resultado": 6,
            "test:resultado": 6,
        }
    )

    card = render_dataset_card(manifest)

    assert "## Category support" in card
    assert "| resultado | 12 | 6 | 6 |" in card


def test_card_flags_category_counts_below_the_support_floor() -> None:
    """#1050/#1051: a category clearing train/val floors but with zero test
    support must be visible as an explicit 0, and an under-floor train/val
    count must be flagged rather than looking identical to a healthy one.
    """
    manifest = _manifest(
        category_counts={
            "train:resultado": 2,  # below MIN_TRAIN_SUPPORT_PER_CATEGORY (10)
            "val:resultado": 5,  # exactly at MIN_VAL_SUPPORT_PER_CATEGORY (5), not flagged
            "test:resultado": 0,  # never observed in the locked test split
        }
    )

    card = render_dataset_card(manifest)

    assert "| resultado | 2* | 5 | 0 |" in card
