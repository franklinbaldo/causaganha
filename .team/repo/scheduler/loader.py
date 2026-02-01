"""Persona loading and prompt parsing for Jules scheduler."""

import sys
from pathlib import Path
from typing import Any

import frontmatter
import jinja2

from repo.scheduler.models import PersonaConfig


class PersonaLoader:
    """Loads and parses persona configurations from .team/personas/."""

    def __init__(self, personas_dir: Path, base_context: dict[str, Any] | None = None):
        """Initialize loader.

        Args:
            personas_dir: Path to .team/personas directory
            base_context: Base template context (repo info, etc.). Optional for simple listing.
        """
        self.personas_dir = personas_dir
        self.base_context = base_context or {}

        # Initialize Jinja environment with FileSystemLoader
        # We point to the templates directory relative to this file
        templates_dir = Path(__file__).parent.parent / "templates"
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader([
                str(templates_dir),
                str(personas_dir),
                ".",  # Allow loading relative to root if needed
            ]),
            undefined=jinja2.Undefined,  # Use lenient Undefined for roster listing
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def load_personas(self, cycle_list: list[str]) -> list[PersonaConfig]:
        """Load all personas in cycle order.

        Args:
            cycle_list: Ordered list of relative paths (e.g., ["personas/curator/prompt.md"])
                       If empty, loads all personas from directory

        Returns:
            List of PersonaConfig in cycle order

        Raises:
            SystemExit: If cycle_list is provided but no valid prompts found
        """
        configs: list[PersonaConfig] = []

        if cycle_list:
            # Load specific personas in cycle order
            base_dir = self.personas_dir.parent
            for rel_path in cycle_list:
                base_path = (base_dir / rel_path).resolve()
                prompt_file = base_path

                # Intelligent extension resolution
                if not prompt_file.exists():
                    # If passed .md but .md.j2 exists
                    if base_path.suffix == ".md" and base_path.with_suffix(".md.j2").exists():
                        prompt_file = base_path.with_suffix(".md.j2")
                    # If passed .md but replaced with .j2 (renamed)
                    elif base_path.suffix == ".md" and base_path.with_suffix(".j2").exists():
                         prompt_file = base_path.with_suffix(".j2")
                    # Append .j2 if missing
                    elif base_path.with_suffix(base_path.suffix + ".j2").exists():
                        prompt_file = base_path.with_suffix(base_path.suffix + ".j2")
                    else:
                        print(f"Cycle prompt not found: {rel_path} (checked {prompt_file})", file=sys.stderr)
                        continue

                try:
                    config = self.load_persona(prompt_file)
                    configs.append(config)
                except Exception as exc:
                    print(f"Failed to load cycle prompt {rel_path}: {exc}", file=sys.stderr)

            if not configs:
                # If cycle list was provided but nothing loaded, return empty list instead of exit
                # This allows callers to handle empty state gracefully
                return []
        else:
            # Load all personas from directory
            # Strategy: find all prompt.* files, prefer .j2 if duplicates exist
            found_personas = {}

            # Scan for .md.j2 and .md
            candidates = sorted(list(self.personas_dir.glob("*/prompt.md.j2")) + list(self.personas_dir.glob("*/prompt.md")))

            for p_file in candidates:
                persona_name = p_file.parent.name
                # If we haven't seen this persona, or if this is a .j2 file (preferred)
                if persona_name not in found_personas or p_file.suffix == ".j2":
                    found_personas[persona_name] = p_file

            for prompt_file in sorted(found_personas.values()):
                try:
                    config = self.load_persona(prompt_file)
                    configs.append(config)
                except Exception as exc:
                    print(f"Failed to load {prompt_file}: {exc}", file=sys.stderr)

        return configs

    def load_persona(self, prompt_file: Path) -> PersonaConfig:
        """Load a single persona configuration.

        Args:
            prompt_file: Path to persona's prompt file

        Returns:
            PersonaConfig with all fields populated

        Raises:
            ValueError: If persona is missing required fields
            OSError: If file cannot be read
        """
        persona_dir = prompt_file.parent
        post = frontmatter.load(prompt_file)

        # Extract metadata
        persona_id = post.metadata.get("id")
        emoji = post.metadata.get("emoji", "")
        description = post.metadata.get("description", "")

        if not persona_id:
            raise ValueError(f"Persona at {prompt_file} is missing 'id' field")

        # Ensure journals directory exists
        self._ensure_journals_directory(persona_dir)

        # Collect journal entries for context
        journal_entries = self._collect_journals(persona_dir)

        # Build template context
        context = {
            **self.base_context,
            "journal_entries": journal_entries,
            "emoji": emoji,
            "id": persona_id,
        }

        # Parse prompt body with Jinja2
        prompt_body = self._render_prompt(post.content, post.metadata, context)

        return PersonaConfig(
            id=persona_id,
            emoji=emoji,
            description=description,
            prompt_body=prompt_body,
            journal_entries=journal_entries,
            path=str(prompt_file),
        )

    def _render_prompt(self, body_template: str, metadata: dict, context: dict) -> str:
        """Render prompt template with context.

        Args:
            body_template: Raw prompt text with Jinja2 templates
            metadata: Persona frontmatter
            context: Template context

        Returns:
            Fully rendered prompt text
        """
        # Load shared blocks
        full_context = {**context, **metadata}

        # Inject Password
        import uuid
        if "id" in full_context:
            full_context["password"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, full_context["id"]))

        # Sprint context removed - personas no longer use sprint planning

        # PRE-RENDER PARTIALS AND BLOCKS
        # This allows using {{ identity_branding }} instead of {% include "partials/identity_branding.md.j2" %}
        # We search in partials/ and blocks/
        for template_name in self.jinja_env.list_templates():
            if template_name.startswith(("partials/", "blocks/")) and template_name.endswith(".j2"):
                # Use filename without extension as variable name
                # e.g. "partials/identity_branding.md.j2" -> "identity_branding"
                # e.g. "blocks/autonomy.md.j2" -> "autonomy_block"
                name = Path(template_name).name.split('.')[0]

                if template_name.startswith("blocks/"):
                    var_name = f"{name}_block"
                else:
                    var_name = name

                try:
                    # Render the partial with current context
                    content = self.jinja_env.get_template(template_name).render(**full_context)
                    full_context[var_name] = content

                    # Aliases
                    if var_name == "celebration":
                        full_context["empty_queue_celebration"] = content
                except Exception:
                    # If rendering fails (e.g. missing vars required by partial), skip or log
                    pass

        # Render final body
        return self.jinja_env.from_string(body_template).render(**full_context).strip()

    def _ensure_journals_directory(self, persona_dir: Path) -> None:
        """Ensure journals/ subdirectory exists for a persona.

        Args:
            persona_dir: Path to persona directory
        """
        journals_dir = persona_dir / "journals"
        journals_dir.mkdir(parents=True, exist_ok=True)

    def _collect_journals(self, persona_dir: Path) -> str:
        """Collect recent journal entries for a persona.

        Args:
            persona_dir: Path to persona directory

        Returns:
            Formatted string with up to 10 most recent journal entries
        """
        journals_dir = persona_dir / "journals"
        if not journals_dir.exists():
            return ""

        # Get sorted journal files (most recent last)
        journal_files = sorted(journals_dir.glob("*.md"))

        # Keep only last 10 entries
        if len(journal_files) > 10:
            journal_files = journal_files[-10:]

        entries = []
        for journal_file in journal_files:
            try:
                content = journal_file.read_text().strip()

                # Strip frontmatter if present
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()

                if content:
                    entries.append(f"\n--- Journal Entry: {journal_file.name} ---\n{content}\n")
            except Exception:
                pass  # Skip malformed journals

        return "\n".join(entries)
