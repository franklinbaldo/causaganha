from pathlib import Path

from typer.testing import CliRunner

from causaganha.cli.commands.backfill import app


runner = CliRunner()


def test_status_no_manifest(tmp_path: Path) -> None:
    """Test status command when no manifest file exists."""
    manifest_file = tmp_path / "missing.csv"
    result = runner.invoke(app, ["status", "--manifest-file", str(manifest_file)])
    assert result.exit_code == 0
    assert "No manifest found" in result.output


def test_status_with_manifest(tmp_path: Path) -> None:
    """Test status command with an existing manifest file."""
    manifest_file = tmp_path / "manifest.csv"
    manifest_file.write_text(
        "tribunal,date,ia_status,djen_status,updated_at\n"
        "TJSP,2024-01-01,uploaded,,2024-01-20T10:00:00\n"
        "TJSP,2024-01-02,,absent,2024-01-20T10:01:00\n"
        "TJRS,2024-01-01,,available,2024-01-20T10:02:00\n"
    )

    result = runner.invoke(app, ["status", "--manifest-file", str(manifest_file)])
    assert result.exit_code == 0
    assert "Uploaded" in result.output
    assert "1" in result.output  # at least one uploaded


def test_reset_no_args() -> None:
    """Test reset command without any arguments fails."""
    result = runner.invoke(app, ["reset"])
    assert result.exit_code == 1


def test_reset_specific_tribunal(tmp_path: Path) -> None:
    """Test reset command for a specific tribunal."""
    manifest_file = tmp_path / "manifest.csv"
    manifest_file.write_text(
        "tribunal,date,ia_status,djen_status,updated_at\n"
        "TJSP,2024-01-01,uploaded,,2024-01-20T10:00:00\n"
        "TJSP,2024-01-02,,absent,2024-01-20T10:01:00\n"
        "TJRS,2024-01-01,uploaded,,2024-01-20T10:02:00\n"
    )

    result = runner.invoke(
        app, ["reset", "--tribunal", "TJSP", "--manifest-file", str(manifest_file)]
    )
    assert result.exit_code == 0
    assert "Reset 2 entries" in result.output

    # Verify TJRS was not affected
    from djen_backup.manifest import SyncManifest

    m = SyncManifest()
    m.load_from_disk(manifest_file)
    tjrs = m.get_status("TJRS", __import__("datetime").date(2024, 1, 1))
    assert tjrs is not None
    assert tjrs.ia_status == "uploaded"


def test_reset_all(tmp_path: Path) -> None:
    """Test reset command with --all resets all entries."""
    manifest_file = tmp_path / "manifest.csv"
    manifest_file.write_text(
        "tribunal,date,ia_status,djen_status,updated_at\n"
        "TJSP,2024-01-01,uploaded,,2024-01-20T10:00:00\n"
        "TJRS,2024-01-01,,absent,2024-01-20T10:02:00\n"
    )

    result = runner.invoke(app, ["reset", "--all", "--manifest-file", str(manifest_file)])
    assert result.exit_code == 0
    assert "Reset 2 entries" in result.output
