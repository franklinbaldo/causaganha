"""Sprint lifecycle management."""

from pathlib import Path

class SprintManager:
    """Manages sprint lifecycle and provides context to personas."""

    SPRINTS_DIR = Path(".team/sprints")
    CURRENT_FILE = SPRINTS_DIR / "current.txt"

    def __init__(self, repo_path: Path = Path()):
        self.repo_path = repo_path
        self.sprints_dir = self.repo_path / self.SPRINTS_DIR
        self.current_file = self.repo_path / self.CURRENT_FILE
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        """Ensure sprint directory structure exists."""
        if not self.sprints_dir.exists():
            self.sprints_dir.mkdir(parents=True)

        if not self.current_file.exists():
            self.current_file.write_text("1\n")
            # Create initial sprint directories
            for i in range(1, 4):
                sprint_dir = self.sprints_dir / f"sprint-{i}"
                sprint_dir.mkdir(exist_ok=True)

    def get_current_sprint(self) -> int:
        """Get the current sprint number."""
        try:
            return int(self.current_file.read_text().strip())
        except (ValueError, FileNotFoundError):
            return 1

    def increment_sprint(self) -> int:
        """Increment to the next sprint and create necessary directories."""
        current = self.get_current_sprint()
        next_sprint = current + 1

        # Update current.txt
        self.current_file.write_text(f"{next_sprint}\n")

        # Create directories for next sprints if they don't exist
        for offset in [0, 1, 2]:
            sprint_num = next_sprint + offset
            sprint_dir = self.sprints_dir / f"sprint-{sprint_num}"
            sprint_dir.mkdir(exist_ok=True)

            # Create README if it doesn't exist
            readme = sprint_dir / "README.md"
            if not readme.exists():
                readme.write_text(f"# Sprint {sprint_num}\n\n**Status:** Planned\n")

        print(f"Sprint incremented: {current} -> {next_sprint}")
        return next_sprint

    def get_sprint_context(self, persona: str) -> str:
        """Generate prompt context for a persona about sprints."""
        current = self.get_current_sprint()
        next_sprint = current + 1
        plus_2 = current + 2

        # List existing plans
        next_dir = self.sprints_dir / f"sprint-{next_sprint}"
        plus_2_dir = self.sprints_dir / f"sprint-{plus_2}"

        next_plans = [p.name for p in next_dir.glob("*-plan.md")] if next_dir.exists() else []
        plus_2_plans = [p.name for p in plus_2_dir.glob("*-plan.md")] if plus_2_dir.exists() else []

        prompt = f"""
## 🏃 Sprint Planning Context

**Current Sprint:** {current}

You are working in Sprint {current}. As part of your work, you should:

### 1. Complete Your Regular Tasks
Execute your normal persona responsibilities as defined in your prompt.

### 2. Read Other Personas' Plans

**For Sprint {next_sprint}:**
"""
        if next_plans:
            prompt += "\n".join([f"- `.team/sprints/sprint-{next_sprint}/{plan}`" for plan in next_plans])
        else:
            prompt += f"(No plans created yet for sprint-{next_sprint})"

        prompt += f"""

**For Sprint {plus_2}:**
"""
        if plus_2_plans:
            prompt += "\n".join([f"- `.team/sprints/sprint-{plus_2}/{plan}`" for plan in plus_2_plans])
        else:
            prompt += f"(No plans created yet for sprint-{plus_2})"

        prompt += f"""

### 3. Provide Feedback

After reading other personas' plans for sprint-{next_sprint}, create:
- `.team/sprints/sprint-{next_sprint}/{persona}-feedback.md`

### 4. Create Your Plans

Create or update your plans for future sprints:
- `.team/sprints/sprint-{next_sprint}/{persona}-plan.md`
- `.team/sprints/sprint-{plus_2}/{persona}-plan.md`

Use the templates in `.team/sprints/TEMPLATE-*.md` as guides.
"""
        return prompt

# Global instance for backward compatibility
sprint_manager = SprintManager()
