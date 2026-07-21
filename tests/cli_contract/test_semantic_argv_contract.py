"""Framework-neutral argv→semantic-config contract gate (RFC 0013).

The Fase 1 characterization tests (`tests/*/test_*_cli_contract.py`) lock
today's Typer/Click behavior via `Command.make_context`, `opts`,
`secondary_opts` — infrastructure that disappears the moment the CLI moves
to Cyclopts. This module is the durable replacement the RFC calls for: it
runs each CLI for real (`CliRunner.invoke`) with the exact argv a
production workflow sends, mocks only the service-layer call the workflow
ultimately reaches, and asserts on the *semantic* configuration that
arrived there — never on Click's parsed-parameter representation. A
Cyclopts port re-runs this exact file unchanged; it is production code
(`src/*/__main__.py`) and Cyclopts-facing test scaffolding still to write
that will need updating, not this file.

Covers the five workflow families the RFC's Fase 1 registered as production
contracts: djen-backup's bare callback (`collect-zips.yml`), `drain`
(`upload-backlog.yml`), `tjro-juris crawl` (`tjro-sync.yml`), `stj-acordaos
upload` (`stj-sync.yml`), `datajud enrich` (`datajud-enrich.yml`) — plus the
specific cases the Fase 2 review flagged as dangerous: `--no-fail-fast`,
the negatable-vs-non-negatable `--use-proxy` pair, `--tipo` repetition, STJ
path defaults, and the complete absence of IA credentials from every
package's semantic parameters (not just their unavailability in
`ctx.params`, which Fase 1 already covered — here, they're never even
accepted as flags).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from datajud.service import EnrichResult
from djen_backup.engine import SyncSummary
from djen_backup.service import PipelineRunConfig
from stj_acordaos.service import UploadResult
from tests.cli_contract.harness import CliContractCase, MockSpec, run_case


# ── djen_backup ─────────────────────────────────────────────────────────

_DJEN_CREDENTIALS = MockSpec(path="djen_backup.service.resolve_ia_auth", return_value="LOW t:t")


def _check_collect_zips_bare(calls) -> None:
    (call,) = calls["main"]
    (config,) = call.args
    assert config == PipelineRunConfig(
        end_date=date.today() - timedelta(days=1),
        lower_bound=date(2020, 1, 1),
        tribunal=None,
        deadline_minutes=17,
        max_items=0,
        workers=8,
        fail_fast=False,  # --no-fail-fast — the RFC's most fragile case
        publish_live_status=False,
        skip_if_mostly_complete=False,
        use_proxy=True,
    )


def _check_bare_no_use_proxy_is_negatable(calls) -> None:
    (call,) = calls["main"]
    (config,) = call.args
    assert config.use_proxy is False


def _check_upload_backlog_drain(calls) -> None:
    (call,) = calls["main"]
    assert call.kwargs["workers"] == 24
    assert call.kwargs["batch_size"] == 200
    assert call.kwargs["deadline_minutes"] == 55

    (proxy_call,) = calls["proxy"]
    assert proxy_call.kwargs["use_proxy"] is True  # drain's --use-proxy is not negatable


DJEN_BACKUP_CASES = [
    CliContractCase(
        label="djen_backup: collect-zips.yml bare callback (--no-fail-fast, --use-proxy)",
        app_path="djen_backup.__main__",
        argv=[
            "--deadline-minutes",
            "17",
            "--workers",
            "8",
            "--start-date",
            "2020-01-01",
            "--use-proxy",
            "--no-fail-fast",
        ],
        mocks={
            "main": MockSpec(
                path="djen_backup.service.run_pipeline",
                return_value=(0, SyncSummary()),
                is_async=True,
            ),
            "credentials": _DJEN_CREDENTIALS,
        },
        check=_check_collect_zips_bare,
    ),
    CliContractCase(
        label="djen_backup: bare callback's --no-use-proxy is negatable (unlike drain's)",
        app_path="djen_backup.__main__",
        argv=["--no-use-proxy"],
        mocks={
            "main": MockSpec(
                path="djen_backup.service.run_pipeline",
                return_value=(0, SyncSummary()),
                is_async=True,
            ),
            "credentials": _DJEN_CREDENTIALS,
        },
        check=_check_bare_no_use_proxy_is_negatable,
    ),
    CliContractCase(
        label="djen_backup: upload-backlog.yml drain (non-negatable --use-proxy)",
        app_path="djen_backup.__main__",
        argv=[
            "drain",
            "--workers",
            "24",
            "--batch-size",
            "200",
            "--deadline-minutes",
            "55",
            "--use-proxy",
        ],
        mocks={
            "main": MockSpec(path="djen_backup.service.run_drain", return_value=0, is_async=True),
            "proxy": MockSpec(
                path="djen_backup.service.resolve_djen_url", return_value="https://x"
            ),
            "credentials": _DJEN_CREDENTIALS,
        },
        check=_check_upload_backlog_drain,
    ),
    CliContractCase(
        label="djen_backup: drain's --use-proxy has no --no-use-proxy pair (usage error)",
        app_path="djen_backup.__main__",
        argv=["drain", "--no-use-proxy"],
        expected_exit_code=2,
    ),
]


# ── tjro_juris ──────────────────────────────────────────────────────────


def _check_tipo_repetition(calls) -> None:
    (call,) = calls["main"]
    data_dir, tipo, ano, mes, desde_ano = call.args
    assert str(data_dir) == "data/tjro-juris"
    assert list(tipo) == ["acordao", "sumula"]  # repeatable option, tuple vs. list doesn't matter
    assert ano is None
    assert mes is None
    assert desde_ano is None


def _check_daily_backfill(calls) -> None:
    (call,) = calls["main"]
    _data_dir, tipo, ano, mes, desde_ano = call.args
    assert list(tipo or []) == []
    assert ano is None
    assert mes is None
    assert desde_ano == 1988  # tjro-sync.yml's cron default when no dispatch input is given


TJRO_JURIS_CASES = [
    CliContractCase(
        label="tjro_juris: --tipo is repeatable, arrives as a sequence in order",
        app_path="tjro_juris.__main__",
        argv=["crawl", "data/tjro-juris", "--tipo", "acordao", "--tipo", "sumula"],
        mocks={"main": MockSpec(path="tjro_juris.service.crawl_juris", return_value=None)},
        check=_check_tipo_repetition,
    ),
    CliContractCase(
        label="tjro_juris: tjro-sync.yml daily cron (--desde-ano 1988 backfill)",
        app_path="tjro_juris.__main__",
        argv=["crawl", "data/tjro-juris", "--desde-ano", "1988"],
        mocks={"main": MockSpec(path="tjro_juris.service.crawl_juris", return_value=None)},
        check=_check_daily_backfill,
    ),
]


# ── stj_acordaos ────────────────────────────────────────────────────────


def _check_stj_upload_path_defaults_and_env_credentials(calls) -> None:
    (call,) = calls["main"]
    data_dir, parquet_path, manifest_path, ia_key, ia_secret = call.args
    assert str(data_dir) == "data/stj"
    assert str(manifest_path) == "data/stj/stj-manifest.csv"
    assert str(parquet_path) == "data/stj/stj-acordaos.parquet"  # default — not in argv at all
    assert ia_key == "sentinel-ia-key"  # from env only, never a CLI flag
    assert ia_secret == "sentinel-ia-secret"  # noqa: S105 — test fixture, not a real credential


STJ_ACORDAOS_CASES = [
    CliContractCase(
        label="stj_acordaos: stj-sync.yml upload — parquet-path default, credentials from env",
        app_path="stj_acordaos.__main__",
        argv=[
            "upload",
            "--data-dir",
            "data/stj",
            "--manifest-path",
            "data/stj/stj-manifest.csv",
        ],
        env={"IA_ACCESS_KEY": "sentinel-ia-key", "IA_SECRET_KEY": "sentinel-ia-secret"},
        mocks={
            "main": MockSpec(
                path="stj_acordaos.service.upload_all",
                return_value=UploadResult(status="nothing_to_do"),
            ),
        },
        check=_check_stj_upload_path_defaults_and_env_credentials,
    ),
    CliContractCase(
        label="stj_acordaos: --ia-key is not a CLI option anymore (usage error)",
        app_path="stj_acordaos.__main__",
        argv=["upload", "--ia-key", "x"],
        expected_exit_code=2,
    ),
]


# ── datajud ─────────────────────────────────────────────────────────────


def _check_datajud_enrich_defaults_and_absent_credentials(calls) -> None:
    (call,) = calls["main"]
    tribunal, data_dir, sources_dir, cnj, cnj_file, limit, _max_age_days, _batch_size = call.args
    assert tribunal == "tjro"
    assert limit == 500
    assert list(cnj or []) == []
    assert cnj_file is None
    assert str(data_dir) == "data/datajud"
    assert str(sources_dir) == "data"
    assert call.kwargs["skip_upload"] is False
    # No IA_ACCESS_KEY/IA_SECRET_KEY set for this case — credentials are
    # absent from argv entirely, and absent from the environment too, so
    # the semantic value reaching the service is simply empty, not missing.
    assert call.kwargs["ia_key"] == ""
    assert call.kwargs["ia_secret"] == ""


DATAJUD_CASES = [
    CliContractCase(
        label="datajud: datajud-enrich.yml daily cron defaults, no credentials in env",
        app_path="datajud.__main__",
        argv=["enrich", "--tribunal", "tjro", "--limit", "500"],
        mocks={
            "main": MockSpec(
                path="datajud.service.enrich",
                return_value=EnrichResult(status="nothing_to_do"),
            ),
        },
        check=_check_datajud_enrich_defaults_and_absent_credentials,
    ),
    CliContractCase(
        label="datajud: --ia-key is not a CLI option anymore (usage error)",
        app_path="datajud.__main__",
        argv=["enrich", "--ia-key", "x"],
        expected_exit_code=2,
    ),
]


ALL_CASES = DJEN_BACKUP_CASES + TJRO_JURIS_CASES + STJ_ACORDAOS_CASES + DATAJUD_CASES


@pytest.mark.parametrize("case", ALL_CASES, ids=[c.label for c in ALL_CASES])
def test_cli_semantic_contract(case, monkeypatch) -> None:
    run_case(case, monkeypatch)
