import subprocess
from pathlib import Path

class GovernanceManager:
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.constitution_path = self.root_dir / ".team" / "CONSTITUTION.md"

    def get_last_rule_change_commit(self) -> str:
        """Find the last commit to the constitution that was NOT a plead."""
        try:
            # We look for commits to the constitution file.
            # We filter out commits that start with "[PLEAD]" in the subject.
            cmd = [
                "git", "log", "--format=%H %s", "--", str(self.constitution_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(" ", 1)
                commit_hash = parts[0]
                subject = parts[1] if len(parts) > 1 else ""
                
                if not subject.strip().startswith("[PLEAD]"):
                    return commit_hash
            return ""
        except subprocess.CalledProcessError:
            return ""

    def get_persona_last_plead_commit(self, persona_id: str) -> str:
        """Find the last [PLEAD] commit for a specific persona."""
        try:
            cmd = [
                "git", "log", "--format=%H %s", "--", str(self.constitution_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split(" ", 1)
                commit_hash = parts[0]
                subject = parts[1] if len(parts) > 1 else ""
                
                if subject.strip().startswith(f"[PLEAD] {persona_id}"):
                    return commit_hash
            return ""
        except subprocess.CalledProcessError:
            return ""

    def is_persona_pleaded(self, persona_id: str) -> bool:
        """
        A persona is pleaded if they have ANY [PLEAD] commit to the Constitution.
        
        Since the constitution is append-only, agreeing to any version 
        (current or historical) is valid for continued participation.
        """
        return self.get_persona_last_plead_commit(persona_id) != ""

    def has_constitution_changed_since_plead(self, persona_id: str) -> bool:
        """Check if constitution has changed since the persona's last plead."""
        persona_plead = self.get_persona_last_plead_commit(persona_id)
        if not persona_plead:
            return True  # No plead = constitution is "new" to them

        last_constitution_commit = self.get_last_rule_change_commit()
        if not last_constitution_commit:
            return False  # No changes to constitution

        # Check if the last constitution change is newer than the persona's plead
        try:
            cmd = ["git", "merge-base", "--is-ancestor", persona_plead, last_constitution_commit]
            result = subprocess.run(cmd)
            # If persona_plead is ancestor of last_constitution_commit, 
            # then constitution HAS changed since the plead
            return result.returncode == 0 and persona_plead != last_constitution_commit
        except subprocess.CalledProcessError:
            return False

    def get_constitution_diff_since_plead(self, persona_id: str) -> str:
        """Get the diff of constitution changes since the persona's last plead."""
        persona_plead = self.get_persona_last_plead_commit(persona_id)
        if not persona_plead:
            return ""
        
        try:
            cmd = ["git", "diff", persona_plead, "HEAD", "--", str(self.constitution_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
