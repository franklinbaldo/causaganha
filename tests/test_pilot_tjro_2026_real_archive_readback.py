"""Tests for the real-Archive read-back helpers used by issue #1471/#1472.

These are the network-free, injectable pieces of
`scripts/benchmarks/pilot_tjro_2026_real_archive_readback.py`: CORS
classification, transient-vs-final failure classification, Parquet magic-byte
verification, and the retry-once probe loop against a mocked transport. The
script's `run()`/`main()` do real HTTPS against archive.org and are not
covered here, matching this repo's existing convention for
`validate_pilot_tjro_2026.py` and `pilot_tjro_2026_query_cost.py`.
"""

from __future__ import annotations

import httpx
import pytest

from scripts.benchmarks.pilot_tjro_2026_real_archive_readback import (
    classify_cors,
    is_transient_failure,
    probe_endpoint,
    verify_parquet_magic,
)


class TestClassifyCors:
    def test_true_when_header_present(self) -> None:
        headers = httpx.Headers({"Access-Control-Allow-Origin": "*"})
        assert classify_cors(headers) is True

    def test_false_when_header_absent(self) -> None:
        headers = httpx.Headers({"Content-Type": "application/octet-stream"})
        assert classify_cors(headers) is False

    def test_case_insensitive(self) -> None:
        headers = httpx.Headers({"access-control-allow-origin": "*"})
        assert classify_cors(headers) is True


class TestVerifyParquetMagic:
    def test_true_for_valid_parquet_head_and_tail(self) -> None:
        assert verify_parquet_magic(b"PAR1restofthehead", b"restofthetailPAR1") is True

    def test_false_when_head_missing_magic(self) -> None:
        assert verify_parquet_magic(b"NOTAPARQUETFILE!", b"restofthetailPAR1") is False

    def test_false_when_tail_missing_magic(self) -> None:
        assert verify_parquet_magic(b"PAR1restofthehead", b"restofthetailXXXX") is False


class TestIsTransientFailure:
    def test_none_for_clean_200(self) -> None:
        response = httpx.Response(200, request=httpx.Request("GET", "https://example.org"))
        assert is_transient_failure(response, None) is None

    def test_none_for_final_404(self) -> None:
        response = httpx.Response(404, request=httpx.Request("GET", "https://example.org"))
        assert is_transient_failure(response, None) is None

    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_reason_for_transient_status_codes(self, status: int) -> None:
        response = httpx.Response(status, request=httpx.Request("GET", "https://example.org"))
        reason = is_transient_failure(response, None)
        assert reason is not None
        assert str(status) in reason

    def test_reason_for_request_error(self) -> None:
        error = httpx.ConnectTimeout("timed out")
        reason = is_transient_failure(None, error)
        assert reason is not None
        assert "timed out" in reason


class TestProbeEndpoint:
    def test_success_on_first_attempt_records_cors_and_bytes(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Access-Control-Allow-Origin": "*"},
                content=b"0123456789ABCDEF",
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        probe = probe_endpoint(client, "https://example.org/file")

        assert probe.ok is True
        assert probe.status_code == 200
        assert probe.attempts == 1
        assert probe.bytes_received == 16
        assert probe.cors_enabled is True
        assert probe.transient_retry_reason is None
        assert probe.error is None

    def test_no_cors_header_is_recorded_as_disabled(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(206, content=b"partial")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        probe = probe_endpoint(client, "https://example.org/file")

        assert probe.ok is True
        assert probe.cors_enabled is False

    def test_retries_once_on_transient_status_then_succeeds(self) -> None:
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] == 1:
                return httpx.Response(503)
            return httpx.Response(200, content=b"ok")

        client = httpx.Client(transport=httpx.MockTransport(handler))
        probe = probe_endpoint(client, "https://example.org/file")

        assert probe.ok is True
        assert probe.attempts == 2
        assert probe.transient_retry_reason == "transient status 503"

    def test_final_404_on_first_attempt_is_not_retried(self) -> None:
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        probe = probe_endpoint(client, "https://example.org/file")

        assert probe.ok is False
        assert probe.status_code == 404
        assert attempts["n"] == 1
        assert probe.transient_retry_reason is None

    def test_still_failing_after_retry_is_reported_as_not_ok(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        probe = probe_endpoint(client, "https://example.org/file")

        assert probe.ok is False
        assert probe.attempts == 2
        assert probe.status_code == 503

    def test_request_error_is_retried_and_reported(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("boom", request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        probe = probe_endpoint(client, "https://example.org/file")

        assert probe.ok is False
        assert probe.status_code is None
        assert probe.attempts == 2
        assert "boom" in (probe.error or "")
