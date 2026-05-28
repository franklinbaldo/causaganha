"""LLM analyzer using LiteLLM for multi-provider support.

Supports OpenRouter free models and Gemini free quota. Models are tried
in priority order; on rate-limit or provider error the next model is used.

Model precedence (default):
    1. gemini/gemini-2.0-flash  — Google free quota, fast, high quality
    2. openrouter/google/gemma-3-27b-it:free  — OpenRouter free tier
    3. openrouter/meta-llama/llama-3.3-70b-instruct:free

Set env vars:
    GEMINI_API_KEY or GOOGLE_API_KEY   for Gemini
    OPENROUTER_API_KEY                 for OpenRouter
"""

from __future__ import annotations

import json
import os
from typing import Any

import structlog

from causaganha.analysis.models import DecisionAnalysis


logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Default free model list — tried in order until one succeeds
# ---------------------------------------------------------------------------

DEFAULT_MODELS: list[str] = [
    "gemini/gemini-2.0-flash",
    "openrouter/google/gemma-3-27b-it:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
]

_SYSTEM_PROMPT = """\
You are an expert Brazilian legal analyst. Extract structured data from DJEN \
(Diário de Justiça Eletrônico Nacional) judicial communications to power a \
lawyer rating system.

OUTCOME — map the dispositivo (operative part) to ONE of:
  "procedente"            — claim granted in full (plaintiff wins)
  "parcialmente procedente" — partially granted (plaintiff wins)
  "improcedente"          — claim denied (defendant wins)
  "acordo"                — settlement homologated (draw)
  "extinto sem mérito"    — dismissed without prejudice (nobody wins)
  "unknown"               — cannot determine

DECISION TYPE:
  "sentença"               — first-instance merit judgment
  "acórdão"                — appellate panel decision
  "decisão interlocutória" — procedural order (set outcome="unknown")

For acórdãos look for "dá/dou provimento", "nega/nego provimento", \
"reforma a sentença" in the dispositivo for the final outcome.

Respond with ONLY valid JSON matching this schema (no markdown fences):
{
  "outcome": "<one of the 6 outcomes>",
  "decision_type": "<sentença|acórdão|decisão interlocutória>",
  "plaintiff_won": <true|false>,
  "confidence_score": <0.0-1.0>,
  "summary": "<one sentence>",
  "decision_reasoning": "<1-2 sentences on legal basis>"
}
"""

_USER_TEMPLATE = """\
Extract structured data from the judicial communication below.

Focus on the dispositivo (operative part after 'ante o exposto', 'posto isso', \
'pelo exposto') to determine outcome.

DOCUMENT:
{text}
"""

# Errors that warrant trying the next model
_RETRYABLE_ERRORS = (
    "rate limit",
    "quota",
    "overloaded",
    "503",
    "529",
    "context length",
)


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(token in msg for token in _RETRYABLE_ERRORS)


def _parse_response(content: str) -> dict[str, Any]:
    """Extract JSON from model response, stripping accidental markdown fences."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        # Drop opening fence (```json or ```) and closing fence
        inner = [line for line in lines[1:] if not line.strip().startswith("```")]
        content = "\n".join(inner)
    return json.loads(content)


class LLMAnalyzer:
    """Judicial decision analyzer backed by LiteLLM.

    Tries models in priority order — on rate-limit or provider error the
    next model is attempted. Caller receives a DecisionAnalysis and the
    name of the model that succeeded.
    """

    def __init__(
        self,
        models: list[str] | None = None,
    ) -> None:
        """Initialize with an ordered list of LiteLLM model identifiers."""
        self.models = models or DEFAULT_MODELS

    async def analyze_text(
        self,
        text: str,
        intimation_id: int | None = None,
    ) -> tuple[DecisionAnalysis, str]:
        """Analyze decision text, returning (DecisionAnalysis, model_used).

        Tries each model in order. Raises RuntimeError if all fail.
        """
        import litellm  # noqa: PLC0415

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(text=text[:4000])},
        ]

        last_exc: Exception | None = None
        for model in self.models:
            try:
                logger.debug("llm_analyzer_attempt", model=model, intimation_id=intimation_id)
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=512,
                )
                content = response.choices[0].message.content or ""
                parsed = _parse_response(content)
                analysis = DecisionAnalysis(
                    intimation_id=intimation_id or 0,
                    outcome=parsed.get("outcome", "unknown"),
                    decision_type=parsed.get("decision_type", "unknown"),
                    plaintiff_won=bool(parsed.get("plaintiff_won", False)),
                    confidence_score=float(parsed.get("confidence_score", 0.5)),
                    summary=parsed.get("summary"),
                    decision_reasoning=parsed.get("decision_reasoning"),
                    analysis_method="llm",
                )
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                logger.warning("llm_parse_error", model=model, error=str(exc))
                last_exc = exc
                continue
            except Exception as exc:
                if _is_retryable(exc):
                    logger.warning(
                        "llm_model_unavailable",
                        model=model,
                        error=str(exc)[:120],
                    )
                    last_exc = exc
                else:
                    logger.exception("llm_analysis_failed", model=model)
                    raise
            else:
                logger.info(
                    "llm_analysis_complete",
                    model=model,
                    outcome=analysis.outcome,
                    confidence=analysis.confidence_score,
                    intimation_id=intimation_id,
                )
                return analysis, model

        msg = f"All LLM models failed. Last error: {last_exc}"
        raise RuntimeError(msg)

    @staticmethod
    def models_from_env() -> list[str]:
        """Return enabled models based on available API keys in environment."""
        available: list[str] = []
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            available.append("gemini/gemini-2.0-flash")
        if os.environ.get("OPENROUTER_API_KEY"):
            available.extend([
                "openrouter/google/gemma-3-27b-it:free",
                "openrouter/meta-llama/llama-3.3-70b-instruct:free",
            ])
        return available or DEFAULT_MODELS
