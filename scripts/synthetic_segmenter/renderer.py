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
    buf.write("Diante de todo o exposto, ")
    buf.write_labeled(SINGLE_ANCHOR_PHRASES["dispositivo_abertura"][0], "dispositivo_abertura")
    buf.write(", ")
    buf.write_labeled(resultado_phrase(spec.outcome), "resultado")
    buf.write(", nos termos ")
    buf.write_labeled(SINGLE_ANCHOR_PHRASES["fundamentacao_legal"][0], "fundamentacao_legal")
    buf.write(". ")


def _render_sentenca_simples(buf: _TextBuilder, spec: DocumentSpec, ids: IdentitySet) -> None:
    _write_pair_section(
        buf,
        "cabecalho",
        body=(
            f"Processo {ids.numero_processo}. Autor: {ids.autor.full_name}. "
            f"Réu: {ids.reu.full_name}."
        ),
    )
    relatorio_body = (
        f"{ids.autor.full_name}, representado por {ids.advogado_autor} ({ids.oab_autor}), "
        f"ajuizou ação em face de {ids.reu.full_name}. "
    )
    if "reported_prior_outcome" in spec.hard_negative_families:
        relatorio_body += render_hard_negative("reported_prior_outcome")
    _write_pair_section(buf, "relatorio", body=relatorio_body)

    merito_body = (
        "Os documentos juntados aos autos demonstram a plausibilidade do direito alegado. "
    )
    buf.write_labeled(PAIR_PHRASES["capitulo_merito"]["inicio"][0], "capitulo_merito_inicio")
    buf.write(f" {merito_body}")
    _write_operative(buf, spec)
    buf.write_labeled(PAIR_PHRASES["capitulo_merito"]["fim"][0], "capitulo_merito_fim")
    buf.write(" ")

    if spec.has_monetary_award:
        honorarios_body = f"Fixo os honorários advocatícios em R$ {2000 + spec.seed % 5000},00. "
    else:
        honorarios_body = "Sem condenação em honorários advocatícios. "
    _write_pair_section(buf, "honorarios", body=honorarios_body)

    if spec.has_costs:
        _write_pair_section(
            buf, "custas", body="A parte sucumbente arca com as custas processuais."
        )

    _write_pair_section(buf, "encerramento", body=f"{ids.juiz}", fim_variant=0)


def _render_acordao_moderno_unanime(
    buf: _TextBuilder, spec: DocumentSpec, ids: IdentitySet
) -> None:
    _write_pair_section(
        buf,
        "cabecalho",
        body=(
            f"Processo {ids.numero_processo}. Apelante: {ids.autor.full_name}. "
            f"Apelado: {ids.reu.full_name}."
        ),
    )
    _write_pair_section(
        buf,
        "ementa",
        body=("APELAÇÃO CÍVEL. RESPONSABILIDADE CIVIL. DANOS MATERIAIS. RECURSO CONHECIDO."),
    )
    relatorio_body = f"Trata-se de recurso interposto por {ids.autor.full_name}. "
    if "reported_prior_outcome" in spec.hard_negative_families:
        relatorio_body += render_hard_negative("reported_prior_outcome")
    _write_pair_section(buf, "relatorio", body=relatorio_body)

    if spec.has_preliminar:
        _write_pair_section(
            buf,
            "preliminar",
            body="Não há nulidades ou vícios processuais a serem sanados de ofício.",
        )

    voto_body = "Presentes os pressupostos de admissibilidade, conheço do recurso. "
    if "quoted_dispositivo" in spec.hard_negative_families:
        voto_body += render_hard_negative("quoted_dispositivo")
    _write_pair_section(buf, "voto", body=voto_body)

    decisorio_body_prefix = "os Desembargadores da Turma Recursal decidiram, "
    buf.write_labeled(PAIR_PHRASES["acordao_decisorio"]["inicio"][0], "acordao_decisorio_inicio")
    buf.write(f", {decisorio_body_prefix}")
    buf.write_labeled(resultado_phrase(spec.outcome), "resultado")
    buf.write(", ")
    buf.write_labeled(PAIR_PHRASES["acordao_decisorio"]["fim"][0], "acordao_decisorio_fim")
    buf.write(" ")

    if spec.has_monetary_award:
        honorarios_body = f"Majoro os honorários recursais para R$ {3000 + spec.seed % 5000},00. "
    else:
        honorarios_body = "Sem honorários recursais. "
    _write_pair_section(buf, "honorarios", body=honorarios_body)

    if spec.has_costs:
        _write_pair_section(buf, "custas", body="Custas pela parte sucumbente.")

    _write_pair_section(buf, "encerramento", body=f"{ids.juiz}, Relator(a)")


_RENDERERS = {
    "sentenca_simples": _render_sentenca_simples,
    "acordao_moderno_unanime": _render_acordao_moderno_unanime,
}


def render(spec: DocumentSpec) -> tuple[str, list[dict], IdentitySet]:
    """Render ``spec`` into ``(text, labels, identities)``.

    ``labels`` offsets are exact by construction (RFC 0011 §4.3) — no
    post-hoc offset computation happens here. Run
    ``transform.check_final_invariants`` (and, for the full mechanical
    check, ``scripts/opf_annotate.py validate``) on the result before
    treating it as a trainable record.
    """
    try:
        render_fn = _RENDERERS[spec.template_family]
    except KeyError:
        msg = f"no renderer for template_family {spec.template_family!r}"
        raise ValueError(msg) from None

    identities = generate_identities(spec.identity_seed)
    buf = _TextBuilder()
    render_fn(buf, spec, identities)
    return buf.build(), buf.labels, identities
