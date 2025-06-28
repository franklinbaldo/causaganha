import json
import shutil
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

from src.ia_database_sync import IADatabaseSync


def test_smart_sync_replication(tmp_path):
    local_db = tmp_path / "db.duckdb"
    local_db.write_text("v1")
    remote_dir = tmp_path / "ia"
    remote_file = remote_dir / "causaganha.duckdb"
    ia_state = {}

    def fake_run(args, capture_output=True, text=True, timeout=None):
        cmd = args[1]
        if cmd == "metadata":
            item = args[2]
            if item == "causaganha-database-live":
                files = []
                if remote_file.exists():
                    files.append({"name": "causaganha.duckdb", "mtime": str(remote_file.stat().st_mtime)})
                return CompletedProcess(args, 0, json.dumps({"files": files}), "")
            return CompletedProcess(args, 1, "", "not found")
        elif cmd == "upload":
            item = args[2]
            src = Path(args[3])
            if item == "causaganha-database-live":
                remote_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, remote_file)
                ia_state["file"] = True
            return CompletedProcess(args, 0, "", "")
        elif cmd == "download":
            item = args[2]
            destdir = Path(args[5])
            if item == "causaganha-database-live":
                dest = destdir / item / "causaganha.duckdb"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(remote_file, dest)
            return CompletedProcess(args, 0, "", "")
        elif cmd == "delete":
            item = args[2]
            if item == "causaganha-database-live" and remote_file.exists():
                remote_file.unlink()
                ia_state.pop("file", None)
            return CompletedProcess(args, 0, "", "")
        return CompletedProcess(args, 0, "", "")

    with patch("src.ia_database_sync.subprocess.run", side_effect=fake_run):
        sync = IADatabaseSync(local_db_path=local_db)
        assert sync.upload_database_to_ia()

        # Local change should trigger upload
        local_db.write_text("v2")
        result = sync.smart_sync()
        assert result == "uploaded_to_ia"
        assert remote_file.read_text() == "v2"

        # Remote newer should trigger download
        remote_file.write_text("v3")
        result = sync.smart_sync(prefer_local=False)
        assert result == "downloaded_from_ia"
        assert local_db.read_text() == "v3"
