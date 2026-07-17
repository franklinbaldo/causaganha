"""Tests for scripts.synthetic_segmenter.llm_judge.

litellm mocking follows the same sys.modules-injection pattern as
tests/test_llm_analyzer_key_rotation.py and test_llm_content.py.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.synthetic_segmenter.llm_judge import (
    JUDGE_VERSION,
    JudgeError,
    _model_family,
    attach_judge_verdict,
    default_judge_models,
    judge_record,
)


def _fake_response(content: str) -> MagicMock:
    resp = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp.choices = [choice]
    return resp


def test_default_judge_models_excludes_generator_models() -> None:
    available = ["gemini/gemini-2.5-flash-lite", "openrouter/model-a", "openrouter/model-b"]
    result = default_judge_models(["gemini/gemini-2.5-flash-lite"], available=available)
    assert result == ["openrouter/model-a", "openrouter/model-b"]


def test_default_judge_models_can_return_empty_list() -> None:
    available = ["gemini/gemini-2.5-flash-lite"]
    result = default_judge_models(["gemini/gemini-2.5-flash-lite"], available=available)
    assert result == []


def test_default_judge_models_uses_env_when_available_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    result = default_judge_models([])
    assert any(model.startswith("gemini/") for model in result)


def test_model_family_recognizes_same_line_different_tier_as_one_family() -> None:
    # This is the exact bug: exact-string exclusion let a generator using
    # gemini-2.5-flash "distinct-family" judge with gemini-2.5-flash-lite,
    # a smaller SKU of the identical model line.
    assert _model_family("gemini/gemini-2.5-flash") == _model_family("gemini/gemini-2.5-flash-lite")


def test_model_family_distinguishes_genuinely_different_vendors() -> None:
    assert _model_family("gemini/gemini-2.5-flash") != _model_family(
        "openrouter/moonshotai/kimi-k2.6:free"
    )
    assert _model_family("openrouter/moonshotai/kimi-k2.6:free") != _model_family(
        "openrouter/meta-llama/llama-3.3-70b-instruct:free"
    )


def test_model_family_strips_openrouter_free_tag() -> None:
    assert _model_family("openrouter/moonshotai/kimi-k2.6:free") == _model_family(
        "openrouter/moonshotai/kimi-k2.6"
    )


def test_default_judge_models_excludes_same_family_different_tier() -> None:
    # The regression this fix targets: gemini-2.5-flash-lite must be
    # excluded when the generator used gemini-2.5-flash, not just when it
    # used the byte-for-byte identical string.
    available = ["gemini/gemini-2.5-flash-lite", "openrouter/moonshotai/kimi-k2.6:free"]
    result = default_judge_models(["gemini/gemini-2.5-flash"], available=available)
    assert result == ["openrouter/moonshotai/kimi-k2.6:free"]


@pytest.mark.asyncio
async def test_judge_record_parses_valid_verdict() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(
        return_value=_fake_response('{"score": 0.8, "defects": ["repetitivo"]}')
    )
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        verdict = await judge_record("texto qualquer", models=["openrouter/model-a"])
    assert verdict["score"] == 0.8
    assert verdict["defects"] == ["repetitivo"]
    assert verdict["model"] == "openrouter/model-a"


@pytest.mark.asyncio
async def test_judge_record_falls_back_on_unparseable_response() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(
        side_effect=[_fake_response("not json"), _fake_response('{"score": 0.5}')]
    )
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        verdict = await judge_record(
            "texto qualquer", models=["openrouter/model-a", "openrouter/model-b"]
        )
    assert verdict["score"] == 0.5
    assert verdict["model"] == "openrouter/model-b"


@pytest.mark.asyncio
async def test_judge_record_rejects_out_of_range_score() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(return_value=_fake_response('{"score": 1.5}'))
    with (
        patch.dict(sys.modules, {"litellm": fake_litellm}),
        pytest.raises(JudgeError, match="All judge models failed"),
    ):
        await judge_record("texto qualquer", models=["openrouter/model-a"])


@pytest.mark.asyncio
async def test_judge_record_raises_when_all_models_fail() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(side_effect=RuntimeError("down"))
    with (
        patch.dict(sys.modules, {"litellm": fake_litellm}),
        pytest.raises(JudgeError),
    ):
        await judge_record("texto qualquer", models=["openrouter/model-a"])


def test_attach_judge_verdict_does_not_mutate_input() -> None:
    info = {"source_type": "fully_synthetic"}
    result = attach_judge_verdict(info, judge_score=0.7, judged_against="v1-corpus")
    assert "judge_score" not in info
    assert result["judge_score"] == 0.7
    assert result["judge_version"] == JUDGE_VERSION
    assert result["judged_against"] == "v1-corpus"


def test_attach_judge_verdict_never_touches_labels() -> None:
    """Structural guarantee: attach_judge_verdict's signature has no label
    parameter at all — it cannot mutate labels even by accident.
    """
    import inspect

    params = inspect.signature(attach_judge_verdict).parameters
    assert "label" not in params
    assert "labels" not in params
