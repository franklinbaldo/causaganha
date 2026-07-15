"""``DocumentSpec`` — the abstract plan a document is rendered from.

RFC 0011 §4.1. Controls structure and generation conditions; carries no
label/offset information itself (that's ``renderer.py``) and no section
prose (that's phrase_banks.py / filler text — Phase 1 has no LLM).

Only two template families ship in this first cut (RFC 0011 §5.1 lists
many more sentença/acórdão variants — deliberately out of scope here, see
the module docstring in ``renderer.py``):

- ``sentenca_simples`` — first-instance, single judge, no preliminar.
- ``acordao_moderno_unanime`` — second-instance, collegiate, unanimous,
  with a preliminar chapter.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


DOC_TYPES = ("sentenca", "acordao")

TEMPLATE_FAMILIES = ("sentenca_simples", "acordao_moderno_unanime")

OUTCOMES = ("procedente", "improcedente", "parcialmente_provido", "provido", "negado_provimento")

NOISE_PROFILES = ("clean", "djen_pdf_extraction")


@dataclass(frozen=True)
class DocumentSpec:
    """The generation plan for one synthetic document.

    ``sections`` is the ordered list of section *base names* the rendered
    document will contain (e.g. ``"relatorio"`` implies both
    ``relatorio_inicio``/``relatorio_fim`` will be rendered) — single-anchor
    categories (``dispositivo_abertura``, ``resultado``, ...) are not
    listed here; the renderer always emits them for the operative part.
    """

    template_family: str
    doc_type: str
    sections: tuple[str, ...]
    outcome: str
    has_monetary_award: bool
    has_costs: bool
    has_preliminar: bool
    has_dissent: bool
    noise_profile: str
    seed: int
    identity_seed: int
    hard_negative_families: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate field values eagerly — fail at construction, not at render time."""
        if self.template_family not in TEMPLATE_FAMILIES:
            msg = f"unknown template_family {self.template_family!r}"
            raise ValueError(msg)
        if self.doc_type not in DOC_TYPES:
            msg = f"unknown doc_type {self.doc_type!r}"
            raise ValueError(msg)
        if self.outcome not in OUTCOMES:
            msg = f"unknown outcome {self.outcome!r}"
            raise ValueError(msg)
        if self.noise_profile not in NOISE_PROFILES:
            msg = f"unknown noise_profile {self.noise_profile!r}"
            raise ValueError(msg)
        if self.doc_type == "sentenca" and self.has_dissent:
            msg = "sentenca cannot have has_dissent=True — voto vencido only exists in acordao"
            raise ValueError(msg)


def sentenca_simples_spec(*, seed: int, identity_seed: int | None = None) -> DocumentSpec:
    """A deterministic, complete first-instance sentença.

    Cabeçalho, relatório, mérito, honorários, custas, encerramento — no
    preliminar, no dissent (sentenças are single-judge).
    """
    rng = random.Random(seed)
    return DocumentSpec(
        template_family="sentenca_simples",
        doc_type="sentenca",
        sections=(
            "cabecalho",
            "relatorio",
            "capitulo_merito",
            "honorarios",
            "custas",
            "encerramento",
        ),
        outcome=rng.choice(("procedente", "improcedente", "parcialmente_provido")),
        has_monetary_award=rng.random() < 0.6,
        has_costs=True,
        has_preliminar=False,
        has_dissent=False,
        noise_profile=rng.choice(NOISE_PROFILES),
        seed=seed,
        identity_seed=identity_seed if identity_seed is not None else seed,
    )


def acordao_moderno_unanime_spec(*, seed: int, identity_seed: int | None = None) -> DocumentSpec:
    """A deterministic, complete second-instance acórdão.

    Cabeçalho, ementa, relatório, preliminar, voto (single reporting
    judge, unanimous — ``has_dissent=False``), acordao_decisorio,
    honorários, custas, encerramento.
    """
    rng = random.Random(seed)
    return DocumentSpec(
        template_family="acordao_moderno_unanime",
        doc_type="acordao",
        sections=(
            "cabecalho",
            "ementa",
            "relatorio",
            "preliminar",
            "voto",
            "acordao_decisorio",
            "honorarios",
            "custas",
            "encerramento",
        ),
        outcome=rng.choice(("provido", "negado_provimento", "parcialmente_provido")),
        has_monetary_award=rng.random() < 0.5,
        has_costs=rng.random() < 0.8,
        has_preliminar=True,
        has_dissent=False,
        noise_profile=rng.choice(NOISE_PROFILES),
        seed=seed,
        identity_seed=identity_seed if identity_seed is not None else seed,
    )


SPEC_BUILDERS = {
    "sentenca_simples": sentenca_simples_spec,
    "acordao_moderno_unanime": acordao_moderno_unanime_spec,
}


def sample_spec(
    template_family: str, *, seed: int, identity_seed: int | None = None
) -> DocumentSpec:
    """Dispatch to the right ``*_spec`` builder by name."""
    try:
        builder = SPEC_BUILDERS[template_family]
    except KeyError:
        msg = f"unknown template_family {template_family!r}, expected one of {TEMPLATE_FAMILIES}"
        raise ValueError(msg) from None
    return builder(seed=seed, identity_seed=identity_seed)
