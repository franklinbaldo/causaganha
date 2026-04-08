import json
from pathlib import Path

from typer.testing import CliRunner

from causaganha.cli.commands.backfill import app


runner = CliRunner()


def test_status_no_state_file(tmp_path: Path) -> None:
    """Test status command when no state file exists."""
    state_file = tmp_path / "missing.json"
    result = runner.invoke(app, ["status", "--backfill-state-file", str(state_file)])
    assert result.exit_code == 0
    assert "No backfill state found" in result.output


def test_status_with_progress(tmp_path: Path) -> None:
    """Test status command with an existing state file."""
    state_file = tmp_path / "state.json"
    state_data = {
        "version": 2,
        "tribunals": {
            "TJSP": {
                "cursor_date": "2023-01-01",
                "empty_streak": 5,
                "stopped": False,
                "last_hit_date": "2023-01-05",
            },
            "TJRS": {
                "cursor_date": "2023-01-02",
                "empty_streak": 60,
                "stopped": True,
                "last_hit_date": "2023-01-10",
            },
        },
    }
    state_file.write_text(json.dumps(state_data))

    result = runner.invoke(app, ["status", "--backfill-state-file", str(state_file)])
    assert result.exit_code == 0
    # Rich table contains tribunal data
    assert "TJRS" in result.output
    assert "TJSP" in result.output
    assert "STOPPED" in result.output
    assert "running" in result.output
    assert "2023-01-02" in result.output
    assert "2023-01-01" in result.output


def test_reset_no_args() -> None:
    """Test reset command without any arguments fails."""
    result = runner.invoke(app, ["reset"])
    assert result.exit_code == 1


def test_reset_specific_tribunal(tmp_path: Path) -> None:
    """Test reset command for a specific tribunal."""
    state_file = tmp_path / "state.json"
    state_data = {
        "version": 2,
        "tribunals": {
            "TJSP": {
                "cursor_date": "2023-01-01",
                "empty_streak": 60,
                "stopped": True,
            },
        },
    }
    state_file.write_text(json.dumps(state_data))

    result = runner.invoke(
        app, ["reset", "--tribunal", "TJSP", "--backfill-state-file", str(state_file)]
    )
    assert result.exit_code == 0
    assert "Reset TJSP" in result.output
    assert "1 tribunal(s) reset" in result.output

    # Verify state was saved
    saved_state = json.loads(state_file.read_text())
    assert saved_state["tribunals"]["TJSP"]["stopped"] is False
    assert saved_state["tribunals"]["TJSP"]["empty_streak"] == 0


def test_reset_all_tribunals(tmp_path: Path) -> None:
    """Test reset command with --all resets only stopped tribunals."""
    state_file = tmp_path / "state.json"
    state_data = {
        "version": 2,
        "tribunals": {
            "TJSP": {
                "cursor_date": "2023-01-01",
                "empty_streak": 60,
                "stopped": True,
            },
            "TJRS": {
                "cursor_date": "2023-01-01",
                "empty_streak": 5,
                "stopped": False,
            },
        },
    }
    state_file.write_text(json.dumps(state_data))

    result = runner.invoke(app, ["reset", "--all", "--backfill-state-file", str(state_file)])
    assert result.exit_code == 0
    assert "Reset TJSP" in result.output
    assert "Reset TJRS" not in result.output
    assert "1 tribunal(s) reset" in result.output

    # Verify state was saved
    saved_state = json.loads(state_file.read_text())
    assert saved_state["tribunals"]["TJSP"]["stopped"] is False
    assert saved_state["tribunals"]["TJSP"]["empty_streak"] == 0
    assert saved_state["tribunals"]["TJRS"]["stopped"] is False


def test_reset_specific_tribunal_not_found(tmp_path: Path) -> None:
    """Test reset command for a tribunal that doesn't exist."""
    state_file = tmp_path / "state.json"
    state_data = {
        "version": 2,
        "tribunals": {
            "TJSP": {
                "cursor_date": "2023-01-01",
                "empty_streak": 60,
                "stopped": True,
            },
        },
    }
    state_file.write_text(json.dumps(state_data))

    result = runner.invoke(
        app, ["reset", "--tribunal", "TJRS", "--backfill-state-file", str(state_file)]
    )
    assert result.exit_code == 0
    assert "not found" in result.output
    assert "Nothing to reset" in result.output
