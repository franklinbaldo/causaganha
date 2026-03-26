import json
from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from causaganha.cli.commands.backfill import app

runner = CliRunner()


def test_status_no_state_file(tmp_path: Path):
    """Test status command when no state file exists."""
    state_file = tmp_path / "missing.json"
    result = runner.invoke(app, ["status", "--backfill-state-file", str(state_file)])
    assert result.exit_code == 0
    assert "No backfill state found" in result.stdout


def test_status_with_progress(tmp_path: Path):
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
    assert "Tribunals: 2 total, 1 running, 1 stopped" in result.stdout

    # Check output format
    assert "TJRS" in result.stdout
    assert "STOPPED" in result.stdout
    assert "cursor=2023-01-02" in result.stdout
    assert "streak= 60" in result.stdout

    assert "TJSP" in result.stdout
    assert "running" in result.stdout
    assert "cursor=2023-01-01" in result.stdout
    assert "streak=  5" in result.stdout


def test_reset_no_args():
    """Test reset command without any arguments fails."""
    result = runner.invoke(app, ["reset"])
    assert result.exit_code == 1
    assert "Error: provide --tribunal CODE or --all" in result.stderr


def test_reset_specific_tribunal(tmp_path: Path):
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
    assert "Reset TJSP" in result.stdout
    assert "1 tribunal(s) reset" in result.stdout

    # Verify state was saved
    saved_state = json.loads(state_file.read_text())
    assert saved_state["tribunals"]["TJSP"]["stopped"] is False
    assert saved_state["tribunals"]["TJSP"]["empty_streak"] == 0


def test_reset_all_tribunals(tmp_path: Path):
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
    assert "Reset TJSP" in result.stdout
    assert "Reset TJRS" not in result.stdout
    assert "1 tribunal(s) reset" in result.stdout

    # Verify state was saved
    saved_state = json.loads(state_file.read_text())
    assert saved_state["tribunals"]["TJSP"]["stopped"] is False
    assert saved_state["tribunals"]["TJSP"]["empty_streak"] == 0
    assert saved_state["tribunals"]["TJRS"]["stopped"] is False


def test_reset_specific_tribunal_not_found(tmp_path: Path):
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
    assert "Tribunal TJRS not found in state." in result.stderr
    assert "Nothing to reset." in result.stdout
