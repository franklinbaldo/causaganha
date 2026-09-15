"""Tests for the CORS regression verdict used by issue #1482's probe.

`evaluate_cors_probe_result` is the network-free, injectable piece of
`scripts/benchmarks/archive_cors_probe.py`: it turns a `CorsProbeResult`
(the parsed outcome of two in-page `fetch()` calls) into a pass/fail
regression verdict. `run_probe`, which drives a real Playwright/Chromium
page against live archive.org, is not covered here, matching this repo's
existing convention for `pilot_tjro_2026_real_archive_readback.py`.
"""

from __future__ import annotations

from scripts.benchmarks.archive_cors_probe import (
    CorsProbeResult,
    FetchOutcome,
    Verdict,
    evaluate_cors_probe_result,
)


def _result(*, metadata: FetchOutcome, download: FetchOutcome) -> CorsProbeResult:
    return CorsProbeResult(
        probe_origin="http://127.0.0.1:1/",
        metadata_endpoint=metadata,
        download_endpoint_range_request=download,
    )


class TestEvaluateCorsProbeResult:
    def test_expected_blocked_passes(self) -> None:
        """Today's real, documented outcome: metadata resolves, download is blocked."""
        result = _result(
            metadata=FetchOutcome(
                url="https://archive.org/metadata/djen-tjro-2026/files",
                ok=True,
                status=200,
                type="cors",
                body_bytes=62834,
            ),
            download=FetchOutcome(
                url="https://archive.org/download/djen-tjro-2026/comunicacoes.parquet",
                ok=False,
                error_name="TypeError",
                error_message="Failed to fetch",
            ),
        )

        verdict = evaluate_cors_probe_result(result)

        assert verdict.passed is True
        assert verdict.verdict is Verdict.EXPECTED_BLOCKED

    def test_download_now_allowed_is_flagged_not_silently_passed(self) -> None:
        """If archive.org ever lifts the block, that is news worth surfacing, not a silent pass."""
        result = _result(
            metadata=FetchOutcome(
                url="https://archive.org/metadata/djen-tjro-2026/files",
                ok=True,
                status=200,
                type="cors",
                body_bytes=62834,
            ),
            download=FetchOutcome(
                url="https://archive.org/download/djen-tjro-2026/comunicacoes.parquet",
                ok=True,
                status=206,
                type="cors",
                body_bytes=16,
            ),
        )

        verdict = evaluate_cors_probe_result(result)

        assert verdict.passed is False
        assert verdict.verdict is Verdict.DOWNLOAD_NOW_ALLOWED

    def test_metadata_endpoint_broken_is_a_real_regression(self) -> None:
        """The metadata endpoint is a positive control unrelated to #1482 -- its failure is new."""
        result = _result(
            metadata=FetchOutcome(
                url="https://archive.org/metadata/djen-tjro-2026/files",
                ok=False,
                error_name="TypeError",
                error_message="Failed to fetch",
            ),
            download=FetchOutcome(
                url="https://archive.org/download/djen-tjro-2026/comunicacoes.parquet",
                ok=False,
                error_name="TypeError",
                error_message="Failed to fetch",
            ),
        )

        verdict = evaluate_cors_probe_result(result)

        assert verdict.passed is False
        assert verdict.verdict is Verdict.METADATA_ENDPOINT_BROKEN

    def test_metadata_ok_but_opaque_type_is_treated_as_broken(self) -> None:
        """A non-'cors' response type on the positive control means CORS support itself changed."""
        result = _result(
            metadata=FetchOutcome(
                url="https://archive.org/metadata/djen-tjro-2026/files",
                ok=True,
                status=0,
                type="opaque",
            ),
            download=FetchOutcome(
                url="https://archive.org/download/djen-tjro-2026/comunicacoes.parquet",
                ok=False,
                error_name="TypeError",
                error_message="Failed to fetch",
            ),
        )

        verdict = evaluate_cors_probe_result(result)

        assert verdict.passed is False
        assert verdict.verdict is Verdict.METADATA_ENDPOINT_BROKEN
