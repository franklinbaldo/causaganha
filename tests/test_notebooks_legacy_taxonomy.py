"""``notebooks/`` must not contain segmenter training notebooks pinned to the
legacy v5 BIO taxonomy (RFC 0001 section 3.5: "Notebooks legados... usam
taxonomia e base antigas (BERTimbau + BIO), divergindo do caminho OPF real
(train_segmenter_colab.ipynb -> scripts). Confundem quem chega no repo.").

``notebooks/`` is the directory newcomers browse to find the current
training path; a stale notebook sitting there next to
``train_segmenter_colab.ipynb`` (the real v7 path) reads as a second,
equally-valid option. This test pins the taxonomy markers those legacy
notebooks are known to hardcode, so a v5/BIO notebook landing back in
``notebooks/`` fails loudly instead of silently confusing the next reader
(see issue #924, section 3.3).
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"

# Markers unique to the legacy v5 taxonomy / BIO scheme — never used by the
# current v7 anchor-span ontology (SPAN_CLASS_NAMES_V7, label_space.json).
LEGACY_MARKERS = ("SPAN_CLASS_NAMES_V5", "B-DISPOSITIVO")


def test_notebooks_do_not_reference_legacy_v5_taxonomy() -> None:
    offenders = []
    for path in sorted(NOTEBOOKS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        hits = [marker for marker in LEGACY_MARKERS if marker in text]
        if hits:
            offenders.append(f"{path.name}: {hits}")

    assert offenders == [], (
        "legacy v5/BIO taxonomy notebook(s) found under notebooks/ — move to "
        f"experiments/archive/ per RFC 0001 section 4.4 item 12: {offenders}"
    )
