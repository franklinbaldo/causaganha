"""Tests for scripts.synthetic_segmenter.llm_content.

litellm lives in the optional ``classify`` dependency group and isn't
installed in the default test environment, so a fake module is injected
into ``sys.modules`` — same pattern as ``tests/test_llm_analyzer_key_rotation.py``.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.synthetic_segmenter.anchor_scrub import find_anchor_occurrences
from scripts.synthetic_segmenter.llm_content import (
    ContentGenerationError,
    generate_section_content,
)


def _fake_response(content: str) -> MagicMock:
    resp = MagicMock()
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
async def test_generate_section_content_returns_text_and_model() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(
        return_value=_fake_response("O autor ajuizou ação alegando cobrança indevida.")
    )
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        text, model = await generate_section_content(
            "relatório",
            doc_type="sentença",
            topic="cobrança indevida",
            models=["gemini/gemini-2.5-flash-lite"],
        )
    assert text == "O autor ajuizou ação alegando cobrança indevida."
    assert model == "gemini/gemini-2.5-flash-lite"


@pytest.mark.asyncio
async def test_generate_section_content_falls_back_to_next_model() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(
        side_effect=[RuntimeError("rate limited"), _fake_response("Texto de fallback.")]
    )
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        text, model = await generate_section_content(
            "mérito",
            doc_type="acordao",
            topic="dano moral",
            models=["gemini/gemini-2.5-flash-lite", "openrouter/some-model"],
        )
    assert text == "Texto de fallback."
    assert model == "openrouter/some-model"
    assert fake_litellm.acompletion.await_count == 2


@pytest.mark.asyncio
async def test_generate_section_content_raises_when_all_models_fail() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(side_effect=RuntimeError("down"))
    with (
        patch.dict(sys.modules, {"litellm": fake_litellm}),
        pytest.raises(ContentGenerationError, match="All LLM models failed"),
    ):
        await generate_section_content(
            "relatório",
            doc_type="sentença",
            topic="x",
            models=["gemini/gemini-2.5-flash-lite"],
        )


@pytest.mark.asyncio
async def test_generate_section_content_treats_empty_response_as_failure() -> None:
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(return_value=_fake_response("   "))
    with (
        patch.dict(sys.modules, {"litellm": fake_litellm}),
        pytest.raises(ContentGenerationError),
    ):
        await generate_section_content(
            "relatório",
            doc_type="sentença",
            topic="x",
            models=["gemini/gemini-2.5-flash-lite"],
        )


@pytest.mark.asyncio
async def test_generate_section_content_uses_models_from_env_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(return_value=_fake_response("Texto qualquer."))
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        _text, model = await generate_section_content("relatório", doc_type="sentença", topic="x")
    assert model.startswith("gemini/")


@pytest.mark.asyncio
async def test_generated_content_can_still_contain_an_anchor_that_scrub_must_catch() -> None:
    """This module never scrubs its own output — the caller must. A response
    that imitates a real anchor phrase is exactly the case anchor_scrub
    exists for (RFC 0011 §8/§6.2): an LLM can produce operative-sounding
    text as easily as a real excerpt can contain one.
    """
    fake_litellm = MagicMock()
    fake_litellm.acompletion = AsyncMock(
        return_value=_fake_response("Ante o exposto, julgo procedente o pedido.")
    )
    with patch.dict(sys.modules, {"litellm": fake_litellm}):
        text, _model = await generate_section_content(
            "relatório",
            doc_type="sentença",
            topic="x",
            models=["gemini/gemini-2.5-flash-lite"],
        )
    assert find_anchor_occurrences(text) != []
