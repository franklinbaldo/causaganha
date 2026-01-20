import os
from pathlib import Path
from typing import List, Dict, Optional
import frontmatter

class SkillsManager:
    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or Path(".team/skills")

    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills by scanning the skills directory for SKILL.md files."""
        skills = []
        if not self.skills_dir.exists():
            return skills

        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                skill_md = skill_path / "SKILL.md"
                if skill_md.exists():
                    try:
                        post = frontmatter.load(skill_md)
                        skills.append({
                            "id": skill_path.name,
                            "name": post.metadata.get("name", skill_path.name),
                            "description": post.metadata.get("description", "No description available."),
                            "path": str(skill_md.absolute())
                        })
                    except Exception:
                        # Fallback if frontmatter fails
                        skills.append({
                            "id": skill_path.name,
                            "name": skill_path.name,
                            "description": "Error reading metadata.",
                            "path": str(skill_md.absolute())
                        })
        return sorted(skills, key=lambda x: x["id"])
