"""Tests for the IA-read retry policy in scripts/render_manifest_parquet.py.

Covers the fix for the transient-timeout failure in run 32025145891
(https://github.com/franklinbaldo/causaganha/actions/runs/32025145891):
_urlopen_bytes retries a few times before giving up, and download_segments
uses a cheaper, bounded retry plus a consecutive-failure circuit breaker so a
real IA outage doesn't multiply the whole compaction cycle's duration by
retrying every remaining segment at full cost.
"""

from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path
from typing import Self

import tenacity


def _load_render_module():
    spec = importlib.util.spec_from_file_location(
        "render_manifest_parquet",
        Path(__file__).resolve().parents[1] / "scripts" / "render_manifest_parquet.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Real backoff (5-30s / 2-4s) would make these tests slow; the retry
    # *count* and *circuit breaker* behavior are what's under test, not the
    # wait duration.
    module._urlopen_bytes.retry.wait = tenacity.wait_none()
    module._urlopen_bytes_segment.retry.wait = tenacity.wait_none()
    return module


class _FlakyUrlopen:
    """Fails ``fail_times`` times then returns ``body`` forever after."""

    def __init__(self, body: bytes, fail_times: int) -> None:
        self.body = body
        self.fail_times = fail_times
        self.calls = 0

    def __call__(self, _url, *, timeout: int) -> Self:
        # urllib.request.urlopen(url, timeout=timeout) always passes timeout
        # by keyword — the param name must match to bind at the call site.
        self.last_timeout = timeout
        self.calls += 1
        if self.calls <= self.fail_times:
            timed_out = "timed out"
            raise urllib.error.URLError(timed_out)
        return self

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc_info: object) -> bool:
        return False

    def read(self):
        return self.body


class _AlwaysFailsUrlopen:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _url, *, timeout: int) -> None:
        self.last_timeout = timeout
        self.calls += 1
        timed_out = "timed out"
        raise urllib.error.URLError(timed_out)


def test_urlopen_bytes_retries_then_succeeds(monkeypatch):
    rmp = _load_render_module()
    flaky = _FlakyUrlopen(b"payload", fail_times=2)
    monkeypatch.setattr(rmp.urllib.request, "urlopen", flaky)

    result = rmp._urlopen_bytes("https://example.org/x", timeout=1)

    assert result == b"payload"
    assert flaky.calls == 3  # 2 failures + 1 success, within stop_after_attempt(3)


def test_urlopen_bytes_exhausts_retries_and_raises(monkeypatch):
    rmp = _load_render_module()
    always_fails = _AlwaysFailsUrlopen()
    monkeypatch.setattr(rmp.urllib.request, "urlopen", always_fails)

    raised = False
    try:
        rmp._urlopen_bytes("https://example.org/x", timeout=1)
    except urllib.error.URLError:
        raised = True

    assert raised, "expected URLError after exhausting retries"
    assert always_fails.calls == 3  # stop_after_attempt(3), no more, no fewer


def test_ensure_base_parquet_returns_none_when_ia_stays_down(tmp_path, monkeypatch):
    rmp = _load_render_module()
    monkeypatch.setattr(rmp, "LOCAL_BASE_PARQUET", tmp_path / "base.parquet")
    monkeypatch.setattr(rmp.urllib.request, "urlopen", _AlwaysFailsUrlopen())

    assert rmp.ensure_base_parquet() is None


def test_download_segments_circuit_breaker_skips_rest_after_threshold(tmp_path, monkeypatch):
    """A fully-down IA should abort quickly, not retry every segment.

    stop_after_attempt(2) per segment x SEGMENT_CIRCUIT_BREAKER_THRESHOLD(2)
    consecutive failures caps total underlying urlopen calls at 4, regardless
    of how many segments are in the batch.
    """
    rmp = _load_render_module()
    monkeypatch.setattr(rmp, "LOCAL_SEGMENT_DIR", tmp_path)
    always_fails = _AlwaysFailsUrlopen()
    monkeypatch.setattr(rmp.urllib.request, "urlopen", always_fails)

    names = [f"manifest-log/seg-{i}.csv" for i in range(10)]
    result = rmp.download_segments(names)

    assert result == []
    max_calls = rmp.SEGMENT_CIRCUIT_BREAKER_THRESHOLD * 2  # attempts per segment
    assert always_fails.calls == max_calls, (
        f"expected the breaker to stop after {rmp.SEGMENT_CIRCUIT_BREAKER_THRESHOLD} "
        f"consecutive failures ({max_calls} urlopen calls), got {always_fails.calls} "
        f"calls across {len(names)} segments"
    )


def test_download_segments_circuit_breaker_resets_on_success(tmp_path, monkeypatch):
    """An isolated bad segment must not trip the breaker for later ones."""
    rmp = _load_render_module()
    monkeypatch.setattr(rmp, "LOCAL_SEGMENT_DIR", tmp_path)

    # fail, succeed, fail, succeed, ... — never two consecutive failures.
    def flaky(url, timeout):
        idx = int(url.rsplit("-", 1)[-1].split(".")[0])
        if idx % 2 == 0:
            timed_out = "timed out"
            raise urllib.error.URLError(timed_out)
        return _FlakyUrlopen(b"data", fail_times=0)(url, timeout=timeout)

    monkeypatch.setattr(rmp.urllib.request, "urlopen", flaky)

    names = [f"manifest-log/seg-{i}.csv" for i in range(6)]
    result = rmp.download_segments(names)

    # odd-indexed segments (1, 3, 5) succeed; the breaker never trips because
    # failures are never consecutive.
    downloaded = [n for n, _ in result]
    assert downloaded == [
        "manifest-log/seg-1.csv",
        "manifest-log/seg-3.csv",
        "manifest-log/seg-5.csv",
    ]
