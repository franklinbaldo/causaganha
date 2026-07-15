"""Optional LLM judge for synthetic-record style (RFC 0011 §9, §14 Phase 3).

Gated on ``diagnostics.py`` existing (RFC 0011 §9: "O juiz LLM não é
requisito para o treino sintético inicial. Antes dele, implementar
diagnósticos baratos e determinísticos") — this module is Phase 3, the
last and most optional layer.

Non-negotiable rules from RFC 0011 §9, enforced by this module's shape,
not just documented:

- **Never edits labels.** ``judge_record`` takes raw ``text``, not a full
  ``{"text", "label", "info"}`` record — it is structurally incapable of
  touching a label list it never receives.
- **Feeds back to the generator, not to individual records.** The judge
  identifies stylistic defects; the caller (a human or an orchestrating
  process) decides whether to adjust phrase banks / ``DocumentSpec``
  weights / mutation ratios and bump ``generator_version`` — this module
  only produces the verdict, never applies it.
- **Distinct model family from the content generator** (RFC 0011 §8) —
  ``default_judge_models`` filters ``LLMAnalyzer.models_from_env()`` to
  exclude whatever models the caller's content generator already used.
- **Never accesses the locked test split.** This module has no path to
  ``data/segmenter_splits/test.jsonl`` and takes no split argument — it
  judges whatever text a caller hands it; keeping test data away from that
  caller is the caller's responsibility (RFC 0011 §12.1's hard
  selection/evaluation separation), not something a judge on raw text
  could enforce by itself.
- **Never replaces real validation.** ``judge_score`` is provenance
  metadata (see ``attach_judge_verdict``), not a gate condition anywhere
  in the training/selection pipeline.

Running this over many records is bulk/repeated LLM work — per the
``llm-work-via-subagents`` skill, an operator driving a real judging
campaign in an agent session should fan out subagents rather than loop
this function in-process. This module itself stays a plain single-call
function so it composes either way.
"""

from __future__ import annotations

import json

import structlog

from causaganha.analysis.llm_analyzer import LLMAnalyzer


logger = structlog.get_logger()

JUDGE_VERSION = "judge-v1"

_SYSTEM_PROMPT = (
    "Você avalia trechos de texto processual fictício gerados sinteticamente "
    "para treino de um modelo de segmentação de decisões judiciais. Julgue "
    "apenas o ESTILO e a NATURALIDADE do texto (não a correção jurídica, "
    "não rótulos, não offsets — isso é decidido por outro processo). "
    "Responda em JSON estrito: "
    '{"score": <0.0 a 1.0, 1.0 = indistinguível de texto real>, '
    '"defects": [<lista curta de defeitos estilísticos observados>]}'
)

_USER_TEMPLATE = "Trecho a avaliar:\n\n{text}"


class JudgeError(RuntimeError):
    """All configured judge models failed, or none returned a parseable verdict."""


def default_judge_models(
    generator_models: list[str] | None = None, *, available: list[str] | None = None
) -> list[str]:
    """Model list for judging, excluding whatever the content generator used.

    ``available`` defaults to ``LLMAnalyzer.models_from_env()``.
    Raises no error if the exclusion empties the list — callers get an
    empty list back and must decide whether to widen it (judging is
    optional; a caller with only one available model family has no
    distinct-family option, and that's a configuration fact, not this
    function's problem to paper over).
    """
    candidates = available if available is not None else LLMAnalyzer.models_from_env()
    excluded = set(generator_models or [])
    return [model for model in candidates if model not in excluded]


def _parse_verdict(content: str) -> dict:
    parsed = json.loads(content)
    if "score" not in parsed:
        msg = "judge response missing 'score' field"
        raise ValueError(msg)
    score = float(parsed["score"])
    if not (0.0 <= score <= 1.0):
        msg = f"judge score {score!r} out of range [0.0, 1.0]"
        raise ValueError(msg)
    return {"score": score, "defects": list(parsed.get("defects", []))}


async def judge_record(text: str, *, models: list[str]) -> dict:
    """Judge one synthetic text's style. Returns ``{"score", "defects", "model"}``.

    Raises ``JudgeError`` if every model in ``models`` fails or returns an
    unparseable verdict. ``models`` is required (no environment fallback)
    — callers must explicitly pick a model family distinct from their
    content generator (see ``default_judge_models``), so there is no safe
    default to fall back to silently here.
    """
    import litellm

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _USER_TEMPLATE.format(text=text)},
    ]

    last_error: str | None = None
    for model in models:
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=0.0,
                max_tokens=300,
            )
            content = response.choices[0].message.content or ""
            verdict = _parse_verdict(content)
        except Exception as exc:
            logger.warning("llm_judge_model_failed", model=model, error=str(exc)[:200])
            last_error = str(exc)
            continue
        logger.info("llm_judge_verdict", model=model, score=verdict["score"])
        return {**verdict, "model": model}

    msg = f"All judge models failed to produce a verdict. Last error: {last_error}"
    raise JudgeError(msg)


def attach_judge_verdict(
    info: dict, *, judge_score: float, judged_against: str, judge_version: str = JUDGE_VERSION
) -> dict:
    """Return a copy of ``info`` with judge provenance fields set (RFC 0011 §9).

    Pure — never mutates ``info`` in place, never touches ``label``. The
    judge score is metadata for humans/generator-tuning to read later, not
    something the training/selection pipeline gates on.
    """
    return {
        **info,
        "judge_score": judge_score,
        "judge_version": judge_version,
        "judged_against": judged_against,
    }
