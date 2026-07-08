"""Tests for stj_acordaos.__main__ — CKAN resource classification.

Regression: the STJ dataset carries a non-JSON "dicionário de dados"
resource (format=CSV) that used to be blindly downloaded as ``.json`` and
later broke DuckDB's ``read_json`` during dedup/upload.
"""

from __future__ import annotations

from stj_acordaos.__main__ import _classify_resource


def test_zip_format_classified_as_zip() -> None:
    assert _classify_resource("ZIP", "https://example.org/x") == "zip"


def test_zip_url_suffix_classified_as_zip_even_without_format() -> None:
    assert _classify_resource("", "https://example.org/x.ZIP") == "zip"


def test_json_format_classified_as_json() -> None:
    assert _classify_resource("JSON", "https://example.org/x") == "json"


def test_json_url_suffix_classified_as_json_even_without_format() -> None:
    assert _classify_resource("", "https://example.org/x.json") == "json"


def test_csv_dictionary_resource_is_skipped_not_treated_as_json() -> None:
    assert _classify_resource("CSV", "https://example.org/dicionario-espelhodoacordao.csv") is None


def test_unknown_format_and_extension_is_skipped() -> None:
    assert _classify_resource("", "https://example.org/readme") is None
