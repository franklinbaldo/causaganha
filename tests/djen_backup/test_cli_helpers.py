from __future__ import annotations

from typing import TYPE_CHECKING

from djen_backup.__main__ import _env_truthy, _load_local_env
from djen_backup.service import DJEN_DIRECT_URL, DJEN_PROXY_FALLBACK_URL, resolve_djen_url


if TYPE_CHECKING:
    from pathlib import Path


def test_load_local_env_reads_missing_keys_only(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IAS3_ACCESS_KEY=from-file\nIAS3_SECRET_KEY='secret-value'\nEXISTING=ignored\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("IAS3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("IAS3_SECRET_KEY", raising=False)
    monkeypatch.setenv("EXISTING", "already-set")

    result = _load_local_env(env_file)

    assert result is not None
    assert result.loaded_keys == ["IAS3_ACCESS_KEY", "IAS3_SECRET_KEY"]
    assert result.path == env_file.resolve()


def test_resolve_djen_url_defaults_to_direct(monkeypatch) -> None:
    monkeypatch.delenv("DJEN_DIRECT_URL", raising=False)
    monkeypatch.delenv("DJEN_PROXY_URL", raising=False)

    assert resolve_djen_url(use_proxy=False) == DJEN_DIRECT_URL


def test_resolve_djen_url_uses_proxy_when_requested(monkeypatch) -> None:
    monkeypatch.delenv("DJEN_PROXY_URL", raising=False)

    assert resolve_djen_url(use_proxy=True) == DJEN_PROXY_FALLBACK_URL


def test_env_truthy_recognizes_proxy_flag(monkeypatch) -> None:
    monkeypatch.setenv("DJEN_USE_PROXY", "true")

    assert _env_truthy("DJEN_USE_PROXY") is True
