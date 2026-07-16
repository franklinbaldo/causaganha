"""Concrete hard-negative injectors (RFC 0011 §5).

Each function returns unlabeled filler text containing an anchor-shaped
phrase that must NOT be labeled — the point is to show the model the same
surface form in a context where it isn't the operative anchor. Renderer
callers splice the returned text into the document at an appropriate
point and record the family name in the record's
``info.hard_negative_families`` (RFC 0011 §5, §15).

Three families ship, the first two directly grounded in the annotation
guideline's anti-patterns section
(``data/segmenter_splits/annotation_guideline_v7.md``), the third added
2026-07-16 from a real-corpus audit (see below):

- ``quoted_dispositivo`` — "Ante o exposto" appearing inside an acórdão's
  individual voto, where only the collegiate ``acordao_decisorio`` is
  operative (guideline: "do not tag a single-judge dispositivo_abertura
  inside an individual voto as the decision's operative opening").
- ``reported_prior_outcome`` — a resultado-shaped phrase describing the
  lower court's prior ruling inside the relatório, which must not be
  tagged ``resultado`` (guideline anti-pattern: "resultado is only the
  operative holding").
- ``preliminar_in_decisorio_summary`` — the word "PRELIMINAR" appearing
  inside the collegiate ``acordao_decisorio``'s own outcome-summary line
  ("PRELIMINAR REJEITADA. NO MÉRITO, RECURSO NÃO PROVIDO..."), which must
  NOT be tagged ``preliminar_inicio``. Every Round A subagent-labeling
  prompt (2026-07-16, 20 real acórdãos) had to carry an explicit warning
  against this exact confusion, because the pattern kept recurring in real
  documents -- a strong signal the model needs the same discriminating
  negative example during training, not just a written instruction to
  human/subagent labelers.
"""

from __future__ import annotations


HARD_NEGATIVE_FAMILIES = (
    "quoted_dispositivo",
    "reported_prior_outcome",
    "preliminar_in_decisorio_summary",
)


def quoted_dispositivo_text() -> str:
    """An individual judge's non-operative "Ante o exposto" inside a voto."""
    return (
        "Em meu entendimento, ante o exposto, a pretensão recursal merece acolhida "
        "parcial, nos termos que exponho a seguir. "
    )


def reported_prior_outcome_text() -> str:
    """A prior-instance outcome described (not decided) inside the relatório."""
    return (
        "O juízo a quo, em sentença anterior, julgou procedente o pedido inicial, "
        "condenando a parte ré ao pagamento dos valores pleiteados. "
    )


def preliminar_in_decisorio_summary_text() -> str:
    """The word PRELIMINAR inside the collegiate outcome-summary line, not a real heading."""
    return "PRELIMINAR REJEITADA. NO MÉRITO, "


_INJECTORS = {
    "quoted_dispositivo": quoted_dispositivo_text,
    "reported_prior_outcome": reported_prior_outcome_text,
    "preliminar_in_decisorio_summary": preliminar_in_decisorio_summary_text,
}


def render_hard_negative(family: str) -> str:
    """Return the filler text for a named hard-negative family."""
    try:
        return _INJECTORS[family]()
    except KeyError:
        msg = f"unknown hard_negative_family {family!r}, expected one of {HARD_NEGATIVE_FAMILIES}"
        raise ValueError(msg) from None
