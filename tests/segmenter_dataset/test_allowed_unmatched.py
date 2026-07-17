from __future__ import annotations

from segmenter_dataset.mechanical import validate_pairs
from segmenter_dataset.schemas import Label


def test_allowed_unmatched_is_scoped_to_the_exact_pair_base() -> None:
    labels = [Label(start=0, end=5, category="cabecalho_inicio")]

    assert (
        validate_pairs(
            labels,
            allowed_unmatched={"cabecalho": "document ends after the opening anchor"},
        )
        == []
    )

    problems = validate_pairs(
        labels,
        allowed_unmatched={"ementa": "wrong pair"},
    )
    assert any("no declared allowed-unmatched reason" in problem for problem in problems)
    assert any("no unmatched pair" in problem for problem in problems)
