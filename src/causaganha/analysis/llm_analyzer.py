"""LLM analyzer using LiteLLM for multi-provider support.

Supports OpenRouter free models and Gemini free quota. Models are tried
in priority order; on rate-limit or provider error the next model is used.

Model precedence (default) — updated May/2026:
    1. gemini/gemini-2.5-flash-lite  — free tier: ~15 RPM, ~1 000 RPD, 250k TPM (most generous)
    2. gemini/gemini-2.5-flash       — free tier: ~10 RPM, ~250 RPD
    3. openrouter/moonshotai/kimi-k2.6:free          — excellent structured JSON adherence
    4. openrouter/google/gemma-4-31b-it:free        — 262K ctx, Apache 2.0
    5. openrouter/meta-llama/llama-3.3-70b-instruct:free  — reliable fallback

NOTE (privacy): Gemini free tier may use inputs for model training.
    → OK for public DJEN data used here.
    → NOT suitable for sensitive SEI documents / legal filings.

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
    "gemini/gemini-2.5-flash-lite",
    "gemini/gemini-2.5-flash",
    "openrouter/moonshotai/kimi-k2.6:free",
    "openrouter/google/gemma-4-31b-it:free",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
]

_SYSTEM_PROMPT = """\
You are an expert Brazilian legal analyst specializing in DJEN \
(Diário de Justiça Eletrônico Nacional) judicial communications.

## STEP 1 — Locate the dispositivo
Look for these markers to find the operative section:
  ante o exposto | posto isso | isso posto | diante do exposto |
  pelo exposto | em face do exposto | por tais fundamentos |
  nestes termos | em conclusão | pelo que exposto | em vista do exposto
The dispositivo is EVERYTHING AFTER the first matching marker.

## STEP 2 — Negation check
If "não" appears within 4 words BEFORE a verb in the dispositivo, \
that match is CANCELLED. E.g. "não julgo procedente" → NOT procedente.

## STEP 3 — Classify OUTCOME (one of six):

**procedente** (plaintiff wins in full):
  KNOWN patterns: julgo procedente | acolho integralmente | condeno o réu |
    defiro o pedido | acolho o pedido | dou provimento | reforma-se a sentença
  WATCH: "julgo procedente em parte" is NOT procedente, it is parcialmente procedente.

**parcialmente procedente** (plaintiff wins partially):
  KNOWN patterns: julgo parcialmente procedente | parcialmente procedente |
    procedente em parte | procedência parcial | dou parcial provimento |
    defiro em parte | acolho em parte | defiro parcialmente

**improcedente** (defendant wins):
  KNOWN patterns: julgo improcedente | rejeito o pedido | nego provimento |
    nego provimento | denego | inadmito | improcedente a ação/pedido |
    mantenho a sentença (when defendant appealed)
  GAP → many improcedente decisions use indirect phrasing ("julgo improcedente"
  buried in long text, or preceded by detailed reasoning). Watch for decisions
  without the exact phrase but with "nego o pedido", "indefiro o pedido",
  "extingo sem prejuízo" or "deixo de acolher".

**acordo** (settlement):
  KNOWN patterns: homologo o acordo | homologo a transação | homologo a avença |
    homologo a composição | conciliação homologada | as partes transigiram |
    as partes chegaram a acordo

**extinto sem mérito** (dismissed on procedural grounds):
  KNOWN patterns: extingo o processo sem resolução | extinto sem julgamento do mérito |
    julgo extinto sem | pronuncio a decadência | pronuncio a prescrição |
    reconheço a prescrição | carência de ação | falta de interesse de agir |
    ilegitimidade ativa/passiva
  GAP → "JULGO EXTINTO O PROCESSO, sem resolução do mérito" (with comma) often \
misses the existing pattern. Also "Reconheço a litispendência" / "Reconheço a \
conexão" / "Reconheço a coisa julgada" as extinction grounds.

**unknown** (cannot determine):
  Use when: decisão interlocutória | despacho | cite-se | intime-se |
    manifeste-se | aguarde-se | abre-se vista | OR text is just a notification \
(edital de citação, mandado de citação, etc.) with no merit decision.

## STEP 4 — DECISION TYPE:
  "sentença"               — first-instance merit judgment
  "acórdão"               — appellate panel (look for: "acordam", "ACORDÃO")
  "decisão interlocutória" — procedural order (no merit ruling)
  Appeal polarity: "dou/dar provimento" = appellant wins; "nego/negar provimento" \
= first-instance upheld. Context about WHO appealed determines plaintiff_won.

## STEP 5 — FASE PROCESSUAL:
  "conhecimento"  — cognição (Procedimento Comum, Juizado, Ação Penal)
  "execução"     — Cumprimento de Sentença, Execução de Título Extrajudicial
  "recursal"      — Apelação, Agravo de Instrumento, Embargos de Declaração
  "cautelar"      — Tutela Provisória, Medida Cautelar
  "unknown"       — cannot determine

Respond with ONLY valid JSON (no markdown fences):
{{
  "outcome": "<one of the 6 outcomes>",
  "decision_type": "<sentença|acórdão|decisão interlocutória>",
  "plaintiff_won": <true|false>,
  "confidence_score": <0.0-1.0>,
  "fase_processual": "<conhecimento|execução|recursal|cautelar|unknown>",
  "classe_processual": "<exact class from document header, e.g. 'Apelação Cível'>",
  "assunto_principal": "<main legal subject, e.g. 'danos morais', 'cobrança', 'alimentos'>",
  "valor_causa": <float in reais or null>,
  "valor_condenacao": <float in reais or null if no monetary award>,
  "proposed_regex": "<Python regex (re.IGNORECASE) for the KEY PHRASE not yet covered by heuristics>",
  "judge_name": "<full judge name or null>",
  "keywords": ["<list of 3-7 words representing content, e.g. 'danos morais', 'inscrição indevida', 'telefonia'>"],
  "legal_bases": ["<list of explicit laws, articles, themes, súmulas, e.g. 'art. 186 CC', 'Súmula 385 STJ', 'Art. 485, V, CPC'>"],
  "precedents": {
    "<CNJ/Precedent Number, e.g. 'Tema 971 STJ' or 'Súmula 381 STJ'>": "<confirmado|distinto|ultrapassado>"
  },
  "summary": "<one sentence>",
  "decision_reasoning": "<1-2 sentences on legal basis>"
}}

For proposed_regex: ONLY propose a NEW pattern that fills a KNOWN GAP in the \
existing heuristics. If the decision was caught by an existing pattern \
(e.g. plain "julgo procedente"), set proposed_regex to null. \
Target patterns the existing classifier misses, like:
  - comma variants: r'JULGO\\s+EXTINTO\\s+O\\s+PROCESSO[,.]?\\s+sem\\s+resolu[cç][aã]o'
  - litispendência: r'RECONHE[CÇ]O\\s+A\\s+LITISPEND[EÊ]NCIA'
  - coisa julgada: r'RECONHE[CÇ]O\\s+A\\s+COISA\\s+JULGADA'
  - indirect improcedente: r'indefiro\\s+o\\s+pedido|nego\\s+o\\s+pedido'
  - edital/notification (unknown): r'EDITAL\\s+DE\\s+CITA[CÇ][AÃ]O'
"""

_USER_TEMPLATE = """\
Extract structured data from the judicial communication below.

Focus on the dispositivo (operative part after 'ante o exposto', 'posto isso', \
'pelo exposto') to determine outcome.

DOCUMENT:
{text}
"""

# ---------------------------------------------------------------------------
# Batch prompt — multiple decisions per API call
# ---------------------------------------------------------------------------

_BATCH_SYSTEM_PROMPT = """\
You are an expert Brazilian legal analyst specializing in DJEN \
(Diário de Justiça Eletrônico Nacional) judicial communications.

## STEP 1 — Locate the dispositivo in each document
Markers: ante o exposto | posto isso | isso posto | diante do exposto |
  pelo exposto | em face do exposto | por tais fundamentos |
  nestes termos | em conclusão

## STEP 2 — Negation check
"não" within 4 words BEFORE a verb CANCELS that match.

## STEP 3 — Classify OUTCOME (one of six):

**procedente** — plaintiff wins in full:
  KNOWN patterns: julgo procedente | acolho integralmente | condeno o réu |
    defiro o pedido | acolho o pedido | dou provimento | reforma-se a sentença
  WATCH: "julgo procedente em parte" → parcialmente procedente (NOT this).

**parcialmente procedente** — plaintiff wins partially:
  KNOWN patterns: julgo parcialmente procedente | parcialmente procedente |
    procedente em parte | procedência parcial | dou parcial provimento |
    defiro em parte | acolho em parte | defiro parcialmente

**improcedente** — defendant wins:
  KNOWN patterns: julgo improcedente | rejeito o pedido | nego provimento |
    denego | inadmito | mantenho a sentença (when defendant appealed)
  GAP: watch for "indefiro o pedido", "nego o pedido", "deixo de acolher",
  or improcedente buried in long appellate reasoning.

**acordo** — settlement:
  KNOWN patterns: homologo o acordo | homologo a transação | homologo a avença |
    homologo a composição | conciliação homologada | as partes transigiram

**extinto sem mérito** — dismissed on procedural grounds:
  KNOWN patterns: extingo o processo sem resolução | extinto sem julgamento do mérito |
    julgo extinto sem | pronuncio a decadência | pronuncio a prescrição |
    reconheço a prescrição | carência de ação | ilegitimidade ativa/passiva
  GAP: "JULGO EXTINTO O PROCESSO, sem resolução do mérito" (comma variant) and
  "Reconheço a litispendência" / "Reconheço a conexão" / "Reconheço a coisa julgada".

**unknown** — use when:
  decisão interlocutória | despacho | cite-se | intime-se | manifeste-se |
  aguarde-se | abre-se vista | edital de citação | mandado de citação

## STEP 4 — DECISION TYPE:
  "sentença" | "acórdão" (look for "acordam", "ACORDÃO") | "decisão interlocutória"
  Appeal polarity: "dou provimento" = appellant wins; "nego provimento" = upheld.
  Context about WHO appealed determines plaintiff_won.

## STEP 5 — FASE PROCESSUAL:
  "conhecimento" | "execução" | "recursal" | "cautelar" | "unknown"

For each document ID, respond with ONLY valid JSON (no markdown fences):
{{
  "<id>": {{
    "outcome": "<one of the 6 outcomes>",
    "decision_type": "<sentença|acórdão|decisão interlocutória>",
    "plaintiff_won": <true|false>,
    "confidence_score": <0.0-1.0>,
    "fase_processual": "<conhecimento|execução|recursal|cautelar|unknown>",
    "classe_processual": "<exact class from header, e.g. 'Apelação Cível'>",
    "assunto_principal": "<main legal subject, e.g. 'danos morais', 'cobrança'>",
    "valor_causa": <float in reais or null>,
    "valor_condenacao": <float in reais or null>,
    "proposed_regex": "<Python regex filling a KNOWN GAP, or null if covered by existing patterns>",
    "judge_name": "<full name or null>",
    "keywords": ["<3-7 words representing content, e.g. 'seguro', 'inadimplemento', 'indenização'>"],
    "legal_bases": ["<explicit laws, articles, súmulas, e.g. 'art. 300 CPC', 'Art. 927 CC'>"],
    "precedents": {
      "<CNJ/Precedent Number, e.g. 'Tema 971 STJ' or 'Súmula 381 STJ'>": "<confirmado|distinto|ultrapassado>"
    },
    "summary": "<one sentence>",
    "decision_reasoning": "<1-2 sentences>"
  }},
  ...
}}

Every ID in the input MUST appear in the response.

For proposed_regex: ONLY propose when the existing patterns would MISS this decision.
  Known gaps to fill:
  - Comma variant extinto: r'JULGO\\s+EXTINTO\\s+O\\s+PROCESSO[,.]?\\s*sem\\s+resolu[cç][aã]o'
  - Litispendência:        r'RECONHE[CÇ]O\\s+A\\s+LITISPEND[EÊ]NCIA'
  - Coisa julgada:         r'RECONHE[CÇ]O\\s+A\\s+COISA\\s+JULGADA'
  - Indirect improcedente: r'indefiro\\s+o\\s+pedido|nego\\s+o\\s+pedido'
  - Edital (unknown):      r'EDITAL\\s+DE\\s+CITA[CÇ][AÃ]O'
  If caught by a KNOWN pattern above, set proposed_regex to null.
"""

_BATCH_DOC_SEPARATOR = "\n\n=== DECISÃO [{doc_id}] ===\n"

_BATCH_USER_TEMPLATE = """\
Analyze all {n} judicial communications below. For each, focus on the \
dispositivo (operative part after 'ante o exposto', 'posto isso', 'pelo exposto').

{documents}

Respond with a single JSON object keyed by document ID.
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


def _build_analysis(parsed: dict[str, Any], intimation_id: int) -> DecisionAnalysis:
    """Build a DecisionAnalysis from a parsed LLM response dict."""
    # Normalize to lowercase: LLMs sometimes return 'UNKNOWN', 'Procedente', etc.
    outcome = str(parsed.get("outcome", "unknown")).lower().strip()
    decision_type = str(parsed.get("decision_type", "unknown")).lower().strip()

    # Parse monetary values robustly (may come as string "R$ 5.000,00" or float 5000.0)
    def _parse_money(val: Any) -> float | None:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        # Strip currency symbols and convert BR format (1.234,56 -> 1234.56)
        s = str(val).strip().replace("R$", "").replace(" ", "")
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None

    return DecisionAnalysis(
        intimation_id=intimation_id,
        outcome=outcome,
        decision_type=decision_type,
        plaintiff_won=bool(parsed.get("plaintiff_won", False)),
        confidence_score=float(parsed.get("confidence_score", 0.5)),
        summary=parsed.get("summary"),
        decision_reasoning=parsed.get("decision_reasoning"),
        analysis_method="llm",
        # Rich fields
        fase_processual=parsed.get("fase_processual"),
        classe_processual=parsed.get("classe_processual"),
        assunto_principal=parsed.get("assunto_principal"),
        valor_causa=_parse_money(parsed.get("valor_causa")),
        valor_condenacao=_parse_money(parsed.get("valor_condenacao")),
        proposed_regex=parsed.get("proposed_regex"),
        judge_name=parsed.get("judge_name"),
        keywords=parsed.get("keywords") or [],
        legal_bases=parsed.get("legal_bases") or [],
    )


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
        """Analyze a single decision text, returning (DecisionAnalysis, model_used).

        Tries each model in order. Raises RuntimeError if all fail.
        For bulk processing prefer analyze_batch() to maximise RPD efficiency.
        """
        import litellm  # noqa: PLC0415

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(text=text)},
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
                analysis = _build_analysis(parsed, intimation_id or 0)
            except (ValueError, KeyError, json.JSONDecodeError) as exc:
                logger.warning(
                    "llm_parse_error",
                    model=model,
                    error=str(exc),
                    raw_content=content[:1000] if "content" in locals() else None,
                )
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

    async def analyze_batch(
        self,
        items: list[tuple[int, str]],
        *,
        max_chars_per_doc: int = 3000,
    ) -> dict[int, tuple[DecisionAnalysis, str]]:
        """Analyze a batch of decisions in a single API call.

        Args:
            items: List of (intimation_id, text) tuples. Should already be
                   shuffled by the caller to avoid ordering bias.
            max_chars_per_doc: Maximum characters per document (ignored).

        Returns:
            Dict mapping intimation_id -> (DecisionAnalysis, model_used).
            Items that fail to parse are omitted (logged as warnings).

        Why batch?
            Gemini 2.5 Flash-Lite free tier: ~1 000 RPD.
            Single calls: 1 000 decisions/day.
            Batch of 20: 20 000 decisions/day — 20x throughput.
        """
        import litellm  # noqa: PLC0415

        # Build the multi-document prompt
        doc_blocks = []
        id_map: dict[str, int] = {}  # str(id) -> intimation_id
        for int_id, text in items:
            key = str(int_id)
            id_map[key] = int_id
            header = _BATCH_DOC_SEPARATOR.format(doc_id=key)
            doc_blocks.append(f"{header}{text}")

        documents = "\n".join(doc_blocks)
        user_content = _BATCH_USER_TEMPLATE.format(n=len(items), documents=documents)

        # Reserve tokens: enriched schema ~600 tokens/doc (dispositivo_snippet +
        # proposed_regex + judge_name + summary + reasoning are verbose)
        # Gemini 2.5 Flash-Lite supports up to 8192 output tokens.
        max_output_tokens = min(8192, 600 * len(items) + 1024)

        messages = [
            {"role": "system", "content": _BATCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # Gather Gemini keys for rotation
        gemini_keys = []
        raw_keys = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY")
        if raw_keys:
            gemini_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        if not gemini_keys:
            gemini_keys = [None]  # fallback to litellm default / system env

        last_exc: Exception | None = None
        for model in self.models:
            is_gemini = model.startswith("gemini/")
            # Rotate keys for Gemini models
            api_keys_to_try = gemini_keys if is_gemini else [None]

            for api_key in api_keys_to_try:
                try:
                    logger.debug(
                        "llm_batch_attempt",
                        model=model,
                        batch_size=len(items),
                        using_key=f"{api_key[:8]}..." if api_key else "default",
                    )

                    # Pass the rotating key directly instead of mutating the
                    # process-wide environment: os.environ is shared across all
                    # concurrent tasks, so writing it here races between batches
                    # (and permanently leaks the last key). litellm resolves the
                    # key from its env defaults when api_key is None.
                    response = await litellm.acompletion(
                        model=model,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=max_output_tokens,
                        api_key=api_key,
                    )
                    content = response.choices[0].message.content or ""
                    batch_parsed = _parse_response(content)
                except (ValueError, KeyError, json.JSONDecodeError) as exc:
                    logger.warning("llm_batch_parse_error", model=model, error=str(exc))
                    last_exc = exc
                    # Don't try other keys for formatting errors, go to next model/next step
                    break
                except Exception as exc:
                    if (
                        _is_retryable(exc)
                        or "quota" in str(exc).lower()
                        or "limit" in str(exc).lower()
                    ):
                        logger.warning(
                            "llm_batch_model_unavailable_or_quota",
                            model=model,
                            error=str(exc)[:120],
                        )
                        last_exc = exc
                        # Try next key or fallback
                        continue
                    # AuthenticationError (401) means key missing/invalid for THIS
                    # provider — skip to next key or model
                    exc_str = str(exc).lower()
                    if "authentication" in exc_str or "401" in exc_str or "missing" in exc_str:
                        logger.warning(
                            "llm_batch_auth_error",
                            model=model,
                            error=str(exc)[:120],
                        )
                        last_exc = exc
                        continue
                    logger.exception("llm_batch_failed", model=model)
                    raise
                else:
                    # Parse individual results
                    results: dict[int, tuple[DecisionAnalysis, str]] = {}
                    for key, val in batch_parsed.items():
                        int_id = id_map.get(key)
                        if int_id is None:
                            logger.warning("llm_batch_unknown_key", key=key)
                            continue
                        try:
                            analysis = _build_analysis(val, int_id)
                            results[int_id] = (analysis, model)
                        except (ValueError, KeyError, TypeError) as exc:
                            logger.warning(
                                "llm_batch_item_parse_error",
                                intimation_id=int_id,
                                error=str(exc),
                            )
                    logger.info(
                        "llm_batch_complete",
                        model=model,
                        batch_size=len(items),
                        parsed=len(results),
                        missing=len(items) - len(results),
                    )
                    return results

        msg = f"All LLM models failed for batch. Last error: {last_exc}"
        raise RuntimeError(msg)

    @staticmethod
    def models_from_env() -> list[str]:
        """Return enabled models based on available API keys in environment."""
        available: list[str] = []
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            # gemini-2.0-flash retired March/2026; use 2.5 series
            available.extend(
                [
                    "gemini/gemini-2.5-flash-lite",  # 1 000 RPD free — most generous
                    "gemini/gemini-2.5-flash",  # 250 RPD free
                ]
            )
        if os.environ.get("OPENROUTER_API_KEY"):
            available.extend(
                [
                    "openrouter/moonshotai/kimi-k2.6:free",
                    "openrouter/google/gemma-4-31b-it:free",
                    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
                ]
            )
        return available or DEFAULT_MODELS
