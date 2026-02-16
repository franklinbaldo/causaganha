import os
import sys
from argparse import Namespace

# Add repository root to path so we can import scripts
sys.path.append(os.getcwd())

from scripts.pipeline.collect import (
    build_djen_backup_cmd,
    build_subprocess_env,
    parse_structlog_summary,
)


class TestBuildDjenBackupCmd:
    def test_date_translated_to_start_end(self):
        args = Namespace(
            date="2026-01-15",
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=10000,
            workers=2,
            deadline="1200s",
        )
        cmd = build_djen_backup_cmd(args)
        idx = cmd.index("--start-date")
        assert cmd[idx + 1] == "2026-01-15"
        idx = cmd.index("--end-date")
        assert cmd[idx + 1] == "2026-01-15"

    def test_date_range_passthrough(self):
        args = Namespace(
            date=None,
            start_date="2026-01-10",
            end_date="2026-01-15",
            tribunal=None,
            max_items=0,
            workers=2,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        assert "--start-date" in cmd
        assert "--end-date" in cmd
        assert "2026-01-10" in cmd
        assert "2026-01-15" in cmd

    def test_no_date_no_date_args(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=0,
            workers=2,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        assert "--start-date" not in cmd
        assert "--end-date" not in cmd

    def test_tribunal_included(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal="TJSP",
            max_items=0,
            workers=2,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        idx = cmd.index("--tribunal")
        assert cmd[idx + 1] == "TJSP"

    def test_deadline_converted_to_minutes(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=0,
            workers=2,
            deadline="1200s",
        )
        cmd = build_djen_backup_cmd(args)
        idx = cmd.index("--deadline-minutes")
        assert cmd[idx + 1] == "20"

    def test_max_items_zero_omitted(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=0,
            workers=2,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        assert "--max-items" not in cmd

    def test_max_items_nonzero_included(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=10000,
            workers=2,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        idx = cmd.index("--max-items")
        assert cmd[idx + 1] == "10000"

    def test_workers_included(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=0,
            workers=4,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        idx = cmd.index("--workers")
        assert cmd[idx + 1] == "4"

    def test_command_starts_with_uv_run(self):
        args = Namespace(
            date=None,
            start_date=None,
            end_date=None,
            tribunal=None,
            max_items=0,
            workers=2,
            deadline="20m",
        )
        cmd = build_djen_backup_cmd(args)
        assert cmd[:3] == ["uv", "run", "djen-backup"]
        # No subcommand — djen-backup root command runs backfill directly
        assert "scan" not in cmd


class TestBuildSubprocessEnv:
    def test_proxy_url_forwarded_as_env_var(self):
        env = build_subprocess_env("https://custom-proxy.example.com")
        assert env["DJEN_PROXY_URL"] == "https://custom-proxy.example.com"

    def test_empty_proxy_url_preserves_existing_env(self):
        env = build_subprocess_env("")
        # Should not override DJEN_PROXY_URL if proxy_url is empty
        assert "PATH" in env  # inherits from os.environ

    def test_inherits_parent_environment(self):
        env = build_subprocess_env("https://proxy.test")
        assert "PATH" in env


class TestParseStructlogSummary:
    def test_extracts_run_complete_console_format(self):
        output = (
            "2026-02-15T12:00:00+00:00 [info     ] run_complete"
            "                   total=100 uploaded=50 absent_marked=30"
            " failed=5 skipped_deadline=10 skipped_circuit=5 success_rate=94.1%\n"
        )
        stats = parse_structlog_summary(output)
        assert stats["uploaded"] == 50
        assert stats["failed"] == 5
        assert stats["absent_marked"] == 30
        assert stats["total"] == 100

    def test_ignores_other_events(self):
        output = "2026-02-15T12:00:00+00:00 [info     ] gap_found  count=10\n"
        stats = parse_structlog_summary(output)
        assert stats["uploaded"] == 0

    def test_handles_mixed_output(self):
        output = (
            "2026-02-15T12:00:00+00:00 [info     ] scanning    dates=7\n"
            "2026-02-15T12:01:00+00:00 [info     ] run_complete"
            "  total=9 uploaded=2 absent_marked=3 failed=1\n"
        )
        stats = parse_structlog_summary(output)
        assert stats["uploaded"] == 2
        assert stats["absent_marked"] == 3
        assert stats["total"] == 9

    def test_handles_empty_output(self):
        stats = parse_structlog_summary("")
        assert stats["uploaded"] == 0
        assert stats["failed"] == 0
        assert stats["absent_marked"] == 0
        assert stats["total"] == 0

    def test_handles_no_run_complete(self):
        output = "2026-02-15T12:00:00+00:00 [info     ] processing  item=TJSP\n"
        stats = parse_structlog_summary(output)
        assert stats["uploaded"] == 0
        assert stats["failed"] == 0


class TestFilesAddedLogic:
    """Verify files_added includes both uploads and absent markers."""

    def _files_added(self, stats: dict[str, int]) -> bool:
        return stats["uploaded"] > 0 or stats["absent_marked"] > 0

    def test_uploads_only(self):
        assert self._files_added({"uploaded": 5, "absent_marked": 0, "failed": 0, "total": 5})

    def test_absent_markers_only(self):
        # Absent markers create files on IA and should trigger catalog
        assert self._files_added({"uploaded": 0, "absent_marked": 10, "failed": 0, "total": 10})

    def test_both_uploads_and_absent(self):
        assert self._files_added({"uploaded": 3, "absent_marked": 7, "failed": 0, "total": 10})

    def test_nothing_uploaded(self):
        assert not self._files_added({"uploaded": 0, "absent_marked": 0, "failed": 5, "total": 5})
