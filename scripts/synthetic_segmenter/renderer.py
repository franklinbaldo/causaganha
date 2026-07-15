"""The deterministic renderer (RFC 0011 §4.3): the only place offsets are born.

Walks a ``DocumentSpec``, writing filler prose (Phase 1 has no LLM — this
is generic boilerplate, not case content) and inserting phrase-bank
anchors, recording each label's start/end at the moment of insertion —
``text[start:end] == anchor`` holds by construction, never by
post-hoc computation.

Guideline rule reproduced here (``annotation_guideline_v7.md``): an
acórdão's operative result is the collegiate ``acordao_decisorio``: this
renderer never labels ``dispositivo_abertura`` inside an acórdão's
``voto`` — only in a ``sentenca``, where the judge IS the decision. The
acórdão template instead uses the ``quoted_dispositivo`` hard negative
(RFC 0011 §5) for the individual voto's non-operative "Ante o exposto".

Only two template families (RFC 0011 §5.1 lists many more — see the
module docstring in ``specs.py`` for the Phase-1 scope note).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.synthetic_segmenter.hard_negatives import render_hard_negative
from scripts.synthetic_segmenter.identities import IdentitySet, generate_identities
from scripts.synthetic_segmenter.phrase_banks import (
    PAIR_PHRASES,
    SINGLE_ANCHOR_PHRASES,
    resultado_phrase,
)


if TYPE_CHECKING:
    from scripts.synthetic_segmenter.specs import DocumentSpec


class _TextBuilder:
    """Append-only text buffer that records character offsets as it grows."""

    def __init__(self) -> None:
        self._parts: list[str] = []
        self._length = 0
        self.labels: list[dict] = []

    def write(self, text: str) -> None:
        self._parts.append(text)
        self._length += len(text)

    def write_labeled(self, text: str, category: str) -> None:
        start = self._length
        self.write(text)
        end = self._length
        self.labels.append({"category": category, "start": start, "end": end})

    def build(self) -> str:
        return "".join(self._parts)


def _write_pair_section(
    buf: _TextBuilder,
    base_name: str,
    *,
    body: str,
    inicio_variant: int = 0,
    fim_variant: int = 0,
    emit_fim: bool = True,
) -> None:
    """Write ``{base}_inicio`` + filler ``body`` + optionally ``{base}_fim``.

    ``emit_fim=False`` produces the RFC 0011 §16.1 item 3 case: a genuine
    unmatched pair (the section has no closing cue in this document) —
    the ``_inicio`` remains a normal positive label; the caller is
    responsible for setting ``info.unmatched_pair = True`` on the record.
    """
    phrases = PAIR_PHRASES[base_name]
    inicio = phrases["inicio"][inicio_variant % len(phrases["inicio"])]
    buf.write_labeled(inicio, f"{base_name}_inicio")
    buf.write(f" {body} ")
    if emit_fim:
        fim = phrases["fim"][fim_variant % len(phrases["fim"])]
        buf.write_labeled(fim, f"{base_name}_fim")


def _write_operative(buf: _TextBuilder, spec: DocumentSpec) -> None:
    """Write dispositivo_abertura + resultado — sentença only.

    Acórdãos get their operative result inside ``acordao_decisorio``
    instead (see module docstring).
    """
    dispositivo_variants = SINGLE_ANCHOR_PHRASES["dispositivo_abertura"]
    fundamentacao_variants = SINGLE_ANCHOR_PHRASES["fundamentacao_legal"]
    buf.write("Diante de todo o exposto, ")
    buf.write_labeled(
        dispositivo_variants[spec.seed % len(dispositivo_variants)], "dispositivo_abertura"
    )
    buf.write(", ")
    buf.write_labeled(resultado_phrase(spec.outcome, variant=spec.seed), "resultado")
    buf.write(", ")
    buf.write_labeled(
        fundamentacao_variants[spec.seed % len(fundamentacao_variants)], "fundamentacao_legal"
    )
    buf.write(". ")


def _render_sentenca_simples(
    buf: _TextBuilder,
    spec: DocumentSpec,
    ids: IdentitySet,
    *,
    merito_body_override: str | None = None,
) -> None:
    seed = spec.seed
    _write_pair_section(
        buf,
        "cabecalho",
        body=(
            f"Processo {ids.numero_processo}. Autor: {ids.autor.full_name}. "
            f"Réu: {ids.reu.full_name}."
        ),
        inicio_variant=seed,
        fim_variant=seed,
    )
    relatorio_body = (
        f"{ids.autor.full_name}, representado por {ids.advogado_autor} ({ids.oab_autor}), "
        f"ajuizou ação em face de {ids.reu.full_name}. "
    )
    if "reported_prior_outcome" in spec.hard_negative_families:
        relatorio_body += render_hard_negative("reported_prior_outcome")
    _write_pair_section(
        buf, "relatorio", body=relatorio_body, inicio_variant=seed, fim_variant=seed
    )

    merito_body = merito_body_override or (
        "Os documentos juntados aos autos demonstram a plausibilidade do direito alegado. "
    )
    capitulo_merito_phrases = PAIR_PHRASES["capitulo_merito"]
    buf.write_labeled(
        capitulo_merito_phrases["inicio"][seed % len(capitulo_merito_phrases["inicio"])],
        "capitulo_merito_inicio",
    )
    buf.write(f" {merito_body}")
    _write_operative(buf, spec)
    buf.write_labeled(
        capitulo_merito_phrases["fim"][seed % len(capitulo_merito_phrases["fim"])],
        "capitulo_merito_fim",
    )
    buf.write(" ")

    if spec.has_monetary_award:
        honorarios_body = f"Fixo os honorários advocatícios em R$ {2000 + spec.seed % 5000},00. "
    else:
        honorarios_body = "Sem condenação em honorários advocatícios. "
    _write_pair_section(
        buf, "honorarios", body=honorarios_body, inicio_variant=seed, fim_variant=seed
    )

    if spec.has_costs:
        _write_pair_section(
            buf,
            "custas",
            body="A parte sucumbente arca com as custas processuais.",
            inicio_variant=seed,
            fim_variant=seed,
        )

    _write_pair_section(
        buf, "encerramento", body=f"{ids.juiz}", inicio_variant=seed, fim_variant=seed
    )


def _render_acordao_moderno_unanime(
    buf: _TextBuilder, spec: DocumentSpec, ids: IdentitySet
) -> None:
    seed = spec.seed
    _write_pair_section(
        buf,
        "cabecalho",
        body=(
            f"Processo {ids.numero_processo}. Apelante: {ids.autor.full_name}. "
            f"Apelado: {ids.reu.full_name}."
        ),
        inicio_variant=seed,
        fim_variant=seed,
    )
    _write_pair_section(
        buf,
        "ementa",
        body=("APELAÇÃO CÍVEL. RESPONSABILIDADE CIVIL. DANOS MATERIAIS. RECURSO CONHECIDO."),
        inicio_variant=seed,
        fim_variant=seed,
    )
    relatorio_body = f"Trata-se de recurso interposto por {ids.autor.full_name}. "
    if "reported_prior_outcome" in spec.hard_negative_families:
        relatorio_body += render_hard_negative("reported_prior_outcome")
    _write_pair_section(
        buf, "relatorio", body=relatorio_body, inicio_variant=seed, fim_variant=seed
    )

    if spec.has_preliminar:
        _write_pair_section(
            buf,
            "preliminar",
            body="Não há nulidades ou vícios processuais a serem sanados de ofício.",
            inicio_variant=seed,
            fim_variant=seed,
        )

    voto_body = "Presentes os pressupostos de admissibilidade, conheço do recurso. "
    if "quoted_dispositivo" in spec.hard_negative_families:
        voto_body += render_hard_negative("quoted_dispositivo")
    _write_pair_section(buf, "voto", body=voto_body, inicio_variant=seed, fim_variant=seed)

    decisorio_phrases = PAIR_PHRASES["acordao_decisorio"]
    decisorio_body_prefix = "os Desembargadores da Turma Recursal decidiram, "
    buf.write_labeled(
        decisorio_phrases["inicio"][seed % len(decisorio_phrases["inicio"])],
        "acordao_decisorio_inicio",
    )
    buf.write(f", {decisorio_body_prefix}")
    buf.write_labeled(resultado_phrase(spec.outcome, variant=seed), "resultado")
    buf.write(", ")
    buf.write_labeled(
        decisorio_phrases["fim"][seed % len(decisorio_phrases["fim"])], "acordao_decisorio_fim"
    )
    buf.write(" ")

    if spec.has_monetary_award:
        honorarios_body = f"Majoro os honorários recursais para R$ {3000 + spec.seed % 5000},00. "
    else:
        honorarios_body = "Sem honorários recursais. "
    _write_pair_section(
        buf, "honorarios", body=honorarios_body, inicio_variant=seed, fim_variant=seed
    )

    if spec.has_costs:
        _write_pair_section(
            buf,
            "custas",
            body="Custas pela parte sucumbente.",
            inicio_variant=seed,
            fim_variant=seed,
        )

    _write_pair_section(
        buf, "encerramento", body=f"{ids.juiz}, Relator(a)", inicio_variant=seed, fim_variant=seed
    )


_RENDERERS = {
    "sentenca_simples": _render_sentenca_simples,
    "acordao_moderno_unanime": _render_acordao_moderno_unanime,
}


def render(
    spec: DocumentSpec, *, merito_body_override: str | None = None
) -> tuple[str, list[dict], IdentitySet]:
    """Render ``spec`` into ``(text, labels, identities)``.

    ``labels`` offsets are exact by construction (RFC 0011 §4.3) — no
    post-hoc offset computation happens here. Run
    ``transform.check_final_invariants`` (and, for the full mechanical
    check, ``scripts/opf_annotate.py validate``) on the result before
    treating it as a trainable record.

    ``merito_body_override`` (RFC 0011 §6.2 hybrid records): replaces the
    generic mérito filler with caller-supplied prose — e.g. a scrubbed,
    fictionalized real excerpt (``hybrid.py``) or LLM-generated content
    (``llm_content.py``). Only ``sentenca_simples`` has a mérito section;
    passing this for any other template family is a caller bug, not a
    silently-ignored no-op.
    """
    if merito_body_override is not None and spec.template_family != "sentenca_simples":
        msg = (
            f"merito_body_override is only supported for sentenca_simples, "
            f"got template_family={spec.template_family!r}"
        )
        raise ValueError(msg)

    try:
        render_fn = _RENDERERS[spec.template_family]
    except KeyError:
        msg = f"no renderer for template_family {spec.template_family!r}"
        raise ValueError(msg) from None

    identities = generate_identities(spec.identity_seed)
    buf = _TextBuilder()
    if spec.template_family == "sentenca_simples":
        render_fn(buf, spec, identities, merito_body_override=merito_body_override)
    else:
        render_fn(buf, spec, identities)
    return buf.build(), buf.labels, identities
