"""Regression test for Gemini key rotation in LLMAnalyzer (Bug B).

Key rotation must pass the rotating key directly to ``litellm.acompletion``
rather than mutating ``os.environ`` — the environment is process-wide and
shared across concurrent tasks, so writing it races between batches and
permanently leaks the last key.

litellm lives in the optional ``classify`` dependency group and isn't installed
in the default test environment, so we inject a fake module into ``sys.modules``
to satisfy the analyzer's lazy ``import litellm``.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from causaganha.analysis.llm_analyzer import LLMAnalyzer


def _fake_response(content: str) -> MagicMock:
    resp = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
async def test_rotating_key_is_passed_to_litellm_not_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "SECRET_ROTATING_KEY")
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(return_value=_fake_response("{}"))

    analyzer = LLMAnalyzer(models=["gemini/gemini-2.5-flash"])
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        await analyzer.analyze_batch([(1, "Julgo procedente o pedido.")])

    # The key was handed to litellm directly...
    fake_litellm.acompletion.assert_awaited_once()
    assert fake_litellm.acompletion.await_args.kwargs["api_key"] == "SECRET_ROTATING_KEY"

    # ...and NOT smuggled through the shared process environment.
    assert "GOOGLE_API_KEY" not in os.environ
    assert os.environ.get("GEMINI_API_KEY") == "SECRET_ROTATING_KEY"  # unchanged by rotation


@pytest.mark.asyncio
async def test_non_gemini_model_passes_none_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(return_value=_fake_response("{}"))

    analyzer = LLMAnalyzer(models=["openrouter/some-model"])
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        await analyzer.analyze_batch([(1, "Julgo improcedente.")])

    fake_litellm.acompletion.assert_awaited_once()
    # litellm resolves the key from its own env defaults when api_key is None.
    assert fake_litellm.acompletion.await_args.kwargs["api_key"] is None
