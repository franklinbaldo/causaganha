"""Trust boundary marker for judicial text content returned by MCP tools (#1616).

``publicacoes_buscar`` and ``decisoes_buscar`` return free text (``trecho``)
extracted from judicial publications and decisions. A third party partially
controls that text and may write it so that it reads like an instruction
aimed at an agent, not a human. The server cannot enforce the downstream
host's tool policy, but it can make the semantic boundary unambiguous and
machine-readable in the response itself: this text is always data to cite,
never a command to execute. Any action beyond citing it is a decision for
the host/agent, never something to infer from the text.
"""

from __future__ import annotations

from typing import Literal


UNTRUSTED_LEGAL_TEXT: Literal["untrusted_legal_text"] = "untrusted_legal_text"
