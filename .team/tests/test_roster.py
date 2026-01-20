"""Tests for the roster CLI command."""
import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from repo.cli.roster import app, get_personas_dir


runner = CliRunner()


class TestGetPersonasDir:
    """Tests for get_personas_dir helper function."""

    def test_finds_jules_personas_dir(self, tmp_path, monkeypatch):
        """Should find .team/personas when it exists."""
        personas_dir = tmp_path / ".team" / "personas"
        personas_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        
        result = get_personas_dir()
        assert result == Path(".team/personas")

    def test_finds_personas_dir(self, tmp_path, monkeypatch):
        """Should find personas/ when .team/personas doesn't exist."""
        personas_dir = tmp_path / "personas"
        personas_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        
        result = get_personas_dir()
        assert result == Path("personas")

    def test_raises_when_not_found(self, tmp_path, monkeypatch):
        """Should raise FileNotFoundError when no personas dir exists."""
        monkeypatch.chdir(tmp_path)
        
        with pytest.raises(FileNotFoundError, match="Could not find personas directory"):
            get_personas_dir()


class TestRosterList:
    """Tests for 'roster list' command."""

    def test_list_shows_personas(self, tmp_path, monkeypatch):
        """Should list personas with emoji and description."""
        personas_dir = tmp_path / ".team" / "personas"
        refactor_dir = personas_dir / "refactor"
        refactor_dir.mkdir(parents=True)
        
        # Create a minimal persona prompt
        (refactor_dir / "prompt.md.j2").write_text("""---
id: refactor
emoji: "🔧"
description: "Refactoring specialist"
---
Content here
""")
        
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        assert "refactor" in result.stdout
        assert "🔧" in result.stdout
        assert "Refactoring" in result.stdout

    def test_list_handles_no_personas(self, tmp_path, monkeypatch):
        """Should show error when no personas found."""
        personas_dir = tmp_path / ".team" / "personas"
        personas_dir.mkdir(parents=True)
        
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["list"])
        
        assert result.exit_code == 1
        assert "No personas found" in result.stdout

    def test_list_truncates_long_descriptions(self, tmp_path, monkeypatch):
        """Should truncate descriptions over 50 chars."""
        personas_dir = tmp_path / ".team" / "personas"
        curator_dir = personas_dir / "curator"
        curator_dir.mkdir(parents=True)
        
        long_desc = "A" * 100  # 100 char description
        (curator_dir / "prompt.md.j2").write_text(f"""---
id: curator
emoji: "🎨"
description: "{long_desc}"
---
""")
        
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        assert "..." in result.stdout  # Truncated


class TestRosterView:
    """Tests for 'roster view <persona>' command."""

    def test_view_shows_persona_not_found(self, tmp_path, monkeypatch):
        """Should show error when persona not found."""
        personas_dir = tmp_path / ".team" / "personas"
        personas_dir.mkdir(parents=True)
        
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["view", "nonexistent"])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_view_missing_personas_dir(self, tmp_path, monkeypatch):
        """Should show error when personas dir doesn't exist."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["view", "any"])
        
        assert result.exit_code == 1


class TestRosterIntegration:
    """Integration tests that use actual personas directory."""

    @pytest.mark.skipif(
        not Path(".team/personas").exists(),
        reason="Requires actual personas directory"
    )
    def test_list_real_personas(self, monkeypatch):
        """Should list real personas when run from repo root."""
        # Find the actual repo root
        repo_root = Path(__file__).parent.parent.parent
        if not (repo_root / ".team" / "personas").exists():
            pytest.skip("Not in expected repo structure")
        
        monkeypatch.chdir(repo_root)
        result = runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        assert "refactor" in result.stdout.lower()
        assert "Total:" in result.stdout
