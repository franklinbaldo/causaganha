from pathlib import Path

PERSONAS_ROOT = Path(".team/personas")

HIRE_TEMPLATE = """---
description: {description}
emoji: {emoji}
id: {id}
hired_by: {hired_by}
---

{{% extends "base/persona.md.j2" %}}

{{% block role %}}
{role}
{{% endblock %}}

{{% block goal %}}
{goal}
{{% endblock %}}

{{% block context %}}
{context}
{{% endblock %}}

{{% block constraints %}}
{constraints}
{{% endblock %}}

{{% block guardrails %}}
{guardrails}
{{% endblock %}}

{{% block verification %}}
{verification}
{{% endblock %}}

{{% block workflow %}}
{{% include "blocks/bdd_technique.md.j2" %}}

{workflow}
{{% endblock %}}
"""

class HireManager:
    def __init__(self, personas_root: Path = PERSONAS_ROOT):
        self.personas_root = personas_root

    def hire_persona(
        self,
        persona_id: str,
        emoji: str,
        description: str,
        role: str,
        goal: str,
        hired_by: str,
        context: str = "TBD",
        constraints: str = "- Follow project conventions",
        guardrails: str = "✅ Always follow BDD principles",
        workflow: str = "1. 🔍 OBSERVE\n2. 🎯 SELECT\n3. 🛠️ IMPLEMENT\n4. ✅ VERIFY",
        verification: str = "uv run pytest"
    ) -> Path:
        """Create a new persona folder and prompt file."""
        persona_id = persona_id.lower().strip().replace(" ", "_")
        target_dir = self.personas_root / persona_id
        
        if target_dir.exists():
            raise ValueError(f"Persona '{persona_id}' already exists")
            
        target_dir.mkdir(parents=True)
        prompt_path = target_dir / "prompt.md.j2"
        
        content = HIRE_TEMPLATE.format(
            id=persona_id,
            emoji=emoji,
            description=description,
            hired_by=hired_by,
            role=role,
            goal=goal,
            context=context,
            constraints=constraints,
            guardrails=guardrails,
            workflow=workflow,
            verification=verification
        )
        
        with open(prompt_path, "w") as f:
            f.write(content)
            
        return prompt_path
