"""Domain models for Jules scheduler.

Minimal models for the simplified scheduler architecture.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaConfig:
    """Immutable configuration for a persona.

    Attributes:
        id: Persona identifier (e.g., "curator", "refactor")
        emoji: Persona emoji (e.g., "🎭", "🔧")
        description: Role summary
        prompt_body: Rendered prompt text to send to Jules
        journal_entries: Recent journal entries for context
        path: Original path to prompt.md file
    """

    id: str
    emoji: str
    description: str
    prompt_body: str
    journal_entries: str
    path: str
