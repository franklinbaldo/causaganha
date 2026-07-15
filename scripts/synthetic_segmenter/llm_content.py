"""LLM-generated section content for Phase 2 hybrid/synthetic records.

RFC 0011 §8, §14. Reuses the LiteLLM access pattern already established in
``causaganha.analysis.llm_analyzer`` — model strings
(``openrouter/<provider>/<model>[:free]``), fallback across providers, and
``LLMAnalyzer.models_from_env()`` for key-driven model selection. RFC 0011
§8 is explicit that this RFC does not invent a second LLM-access pattern.

**What the LLM is allowed to decide, and what it is never allowed to
decide:** it produces free narrative filler for one section's body (case
facts, procedural narrative) — nothing else. It never chooses labels or
offsets (RFC 0011 §4.3: "O LLM nunca decide offsets ou rótulos finais, em
nenhuma fase."). The renderer inserts anchors and records offsets around
whatever text this module returns, exactly as it does for the Phase 1
generic filler prose.

Generated content still needs ``anchor_scrub.scrub_excerpt`` treatment
before being folded into a record body: an LLM can reproduce a real anchor
phrase by imitation just as easily as a real excerpt can contain one. This
module deliberately does not call ``anchor_scrub`` itself — that stays the
caller's explicit step, matching ``corpus_stats.py``'s "caller does the
filtering" pattern rather than hiding a safety-critical step inside a
generation call.
"""

from __future__ import annotations

import structlog

from causaganha.analysis.llm_analyzer import LLMAnalyzer


logger = structlog.get_logger()

_SYSTEM_PROMPT = (
    "Você escreve trechos de narrativa processual fictícia em português "
    "brasileiro, no estilo de decisões judiciais brasileiras. Nunca inclua "
    "as fórmulas 'Ante o exposto', 'Pelo exposto', 'Posto isso', 'Diante do "
    "exposto', 'É o relatório.', nem qualquer fórmula de resultado "
    "operativo ('julgo procedente', 'dou provimento', 'nego provimento', "
    "etc.) — essas fórmulas são inseridas separadamente por outro "
    "processo, nunca por você. Escreva apenas narrativa factual ou "
    "processual fictícia, sem essas fórmulas, sem nomes de pessoas reais, "
    "sem números de processo reais."
)

_USER_TEMPLATE = (
    "Escreva um trecho de {section_kind} (2 a 4 frases) para um {doc_type} "
    "fictício sobre o tema: {topic}. Responda apenas com o texto do "
    "trecho, sem comentários, sem aspas, sem markdown."
)


class ContentGenerationError(RuntimeError):
    """Every configured model failed to produce usable content."""


async def generate_section_content(
    section_kind: str,
    *,
    doc_type: str,
    topic: str,
    models: list[str] | None = None,
) -> tuple[str, str]:
    """Generate free narrative filler for one document section.

    Returns ``(text, model_used)``. Tries each model in ``models`` (or
    ``LLMAnalyzer.models_from_env()`` if omitted) in order; raises
    ``ContentGenerationError`` if every model fails or returns empty
    content.

    The caller MUST still run the result through
    ``anchor_scrub.scrub_excerpt`` before folding it into a record body —
    this function does not scrub its own output (see module docstring).
    """
    import litellm

    resolved_models = models or LLMAnalyzer.models_from_env()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _USER_TEMPLATE.format(
                section_kind=section_kind, doc_type=doc_type, topic=topic
            ),
        },
    ]

    last_error: str | None = None
    for model in resolved_models:
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=400,
            )
        except Exception as exc:
            logger.warning("llm_content_model_failed", model=model, error=str(exc)[:200])
            last_error = str(exc)
            continue

        content = (response.choices[0].message.content or "").strip()
        if content:
            logger.info(
                "llm_content_generated",
                model=model,
                section_kind=section_kind,
                doc_type=doc_type,
                chars=len(content),
            )
            return content, model
        logger.warning("llm_content_empty_response", model=model)
        last_error = f"model {model} returned empty content"

    msg = f"All LLM models failed to generate {section_kind!r} content. Last error: {last_error}"
    raise ContentGenerationError(msg)
