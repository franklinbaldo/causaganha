"""Regression gate for #1608/TM-01: workflow_dispatch inputs must never
become shell code.

``docs/SECURITY_THREAT_MODEL.md`` TM-01 documents the invariant this file
enforces: a ``workflow_dispatch`` input is attacker-controlled text and must
enter a job only as a validated, typed argument to a fixed command — never
spliced into a ``run:`` script body (GitHub Actions substitutes ``${{ }}``
expressions as literal text *before* bash parses the script, so a bare
``${{ inputs.x }}`` inside a script is a code-injection point regardless of
surrounding quotes) and never reinterpreted a second time via ``eval``.

A live pre-fix demonstration (see
``knowledge/agent-runs/2026-09-24-exciting-mccarthy-1c8jcc/evidence/
evidence-red-workflow-injection-demo.md``) confirmed this was genuinely
exploitable in ``tjro-sync.yml``: a crafted ``tjro_mes`` value executed an
arbitrary command in a job carrying Internet Archive credentials. Auditing
every workflow with ``workflow_dispatch.inputs`` (required by #1608's own
"implementação esperada") found the same pattern in five more files, two of
them also secret-bearing.

Each test below extracts the *real* ``run:`` script for the fixed step
(via ``yaml.safe_load`` — no hand copy that could drift from the file) and
executes it through a real ``bash`` subprocess with a stub ``uv`` on
``PATH``, so this exercises the actual shell logic, not a reimplementation.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# Shell metacharacter payloads that must never be re-interpreted as shell
# syntax, whatever a dispatch input's declared "format" is.
METACHARACTER_PAYLOADS = [
    "2024; touch pwned",
    "2024`touch pwned`",
    "2024$(touch pwned)",
    "2024\ntouch pwned",
    '2024" ; touch pwned; echo "',
]


def _step(workflow_file: str, job_name: str, step_name: str) -> dict:
    workflow = yaml.safe_load((WORKFLOWS_DIR / workflow_file).read_text(encoding="utf-8"))
    steps = workflow["jobs"][job_name]["steps"]
    (step,) = (s for s in steps if s.get("name") == step_name)
    return step


def _run_script(
    workflow_file: str,
    job_name: str,
    step_name: str,
    env: dict[str, str],
    tmp_path: Path,
    matrix: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute a step's real ``run:`` script with a stub ``uv`` on PATH.

    The stub records each invocation's argv (JSON-encoded, one call per
    line) to ``ARGV_LOG`` instead of touching the network/Internet Archive,
    so tests can assert exactly what command the script would have run.

    ``matrix`` splices ``${{ matrix.KEY }}`` expressions the same way
    GitHub Actions itself would — those values come from the fixed matrix
    list declared in the workflow file, not from an attacker-controlled
    dispatch input, so (unlike ``inputs.*``/``github.event.inputs.*``)
    leaving them as literal ``${{ }}`` splices in the script is not the
    vulnerability this file guards against.
    """
    script = _step(workflow_file, job_name, step_name)["run"]
    for key, value in (matrix or {}).items():
        script = script.replace(f"${{{{ matrix.{key} }}}}", value)

    argv_log = tmp_path / "argv.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['ARGV_LOG'], 'a') as f:\n"
        "    f.write(json.dumps(sys.argv[1:]) + chr(10))\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

    script_path = tmp_path / "script.sh"
    script_path.write_text(script)

    run_env = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "ARGV_LOG": str(argv_log),
        **env,
    }
    result = subprocess.run(
        ["bash", str(script_path)],
        cwd=tmp_path,
        env=run_env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    result.argv_calls = (  # type: ignore[attr-defined]
        [json.loads(line) for line in argv_log.read_text().splitlines()]
        if argv_log.exists()
        else []
    )
    return result


def _assert_no_dispatch_splice_or_eval(workflow_file: str, job_name: str, step_name: str) -> None:
    script = _step(workflow_file, job_name, step_name)["run"]
    assert "eval" not in script, f"{workflow_file}::{step_name} must not reinterpret via eval"
    assert "${{ inputs." not in script, (
        f"{workflow_file}::{step_name} must not splice a dispatch input directly into the script"
    )
    assert "${{ github.event.inputs." not in script, (
        f"{workflow_file}::{step_name} must not splice a dispatch input directly into the script"
    )


# ---------------------------------------------------------------------------
# tjro-sync.yml — "Crawl JURIS"
# ---------------------------------------------------------------------------


def test_tjro_sync_crawl_has_no_eval_or_spliced_inputs() -> None:
    _assert_no_dispatch_splice_or_eval("tjro-sync.yml", "tjro", "Crawl JURIS")


@pytest.mark.parametrize("field", ["TJRO_ANO", "TJRO_MES", "TJRO_DESDE_ANO"])
@pytest.mark.parametrize("payload", METACHARACTER_PAYLOADS)
def test_tjro_sync_rejects_metacharacter_payloads(field: str, payload: str, tmp_path: Path) -> None:
    env = {
        "TJRO_ANO": "",
        "TJRO_MES": "",
        "TJRO_DESDE_ANO": "",
        "TJRO_TIPOS": "",
        "TJRO_EVENT_NAME": "workflow_dispatch",
        field: payload,
    }
    result = _run_script("tjro-sync.yml", "tjro", "Crawl JURIS", env, tmp_path)
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]
    assert not (tmp_path / "pwned").exists()


def test_tjro_sync_rejects_unknown_tipo(tmp_path: Path) -> None:
    env = {
        "TJRO_ANO": "",
        "TJRO_MES": "",
        "TJRO_DESDE_ANO": "",
        "TJRO_TIPOS": "NAO_E_UM_TIPO_VALIDO",
        "TJRO_EVENT_NAME": "workflow_dispatch",
    }
    result = _run_script("tjro-sync.yml", "tjro", "Crawl JURIS", env, tmp_path)
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]


def test_tjro_sync_valid_dispatch_inputs_produce_expected_argv(tmp_path: Path) -> None:
    env = {
        "TJRO_ANO": "2024",
        "TJRO_MES": "",
        "TJRO_DESDE_ANO": "",
        "TJRO_TIPOS": "SENTENÇA,ACÓRDÃO",
        "TJRO_EVENT_NAME": "workflow_dispatch",
    }
    result = _run_script("tjro-sync.yml", "tjro", "Crawl JURIS", env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "--no-dev",
            "tjro-juris",
            "crawl",
            "data/tjro-juris",
            "--ano",
            "2024",
            "--tipo",
            "SENTENÇA",
            "--tipo",
            "ACÓRDÃO",
        ]
    ]


def test_tjro_sync_cron_defaults_to_full_backfill(tmp_path: Path) -> None:
    """Scheduled runs with no dispatch inputs still default to --desde-ano 1988."""
    env = {
        "TJRO_ANO": "",
        "TJRO_MES": "",
        "TJRO_DESDE_ANO": "",
        "TJRO_TIPOS": "",
        "TJRO_EVENT_NAME": "schedule",
    }
    result = _run_script("tjro-sync.yml", "tjro", "Crawl JURIS", env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        ["run", "--no-dev", "tjro-juris", "crawl", "data/tjro-juris", "--desde-ano", "1988"]
    ]


# ---------------------------------------------------------------------------
# datajud-enrich.yml — "Enrich CNJs with DataJud metadata"
# ---------------------------------------------------------------------------


def test_datajud_enrich_has_no_eval_or_spliced_inputs() -> None:
    _assert_no_dispatch_splice_or_eval(
        "datajud-enrich.yml", "enrich", "Enrich CNJs with DataJud metadata"
    )


@pytest.mark.parametrize(
    "env_overrides",
    [
        {"DATAJUD_TRIBUNAL_INPUT": "tjro; touch pwned"},
        {"DATAJUD_TRIBUNAL_INPUT": "../tjro"},
        {"DATAJUD_LIMITE_INPUT": "500 && touch pwned"},
        {"DATAJUD_LIMITE_INPUT": "$(touch pwned)"},
    ],
)
def test_datajud_enrich_rejects_malicious_inputs(
    env_overrides: dict[str, str], tmp_path: Path
) -> None:
    env = {
        "DATAJUD_TRIBUNAL_INPUT": "tjro",
        "DATAJUD_LIMITE_INPUT": "500",
        "DATAJUD_SKIP_UPLOAD_INPUT": "false",
        **env_overrides,
    }
    result = _run_script(
        "datajud-enrich.yml", "enrich", "Enrich CNJs with DataJud metadata", env, tmp_path
    )
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]
    assert not (tmp_path / "pwned").exists()


def test_datajud_enrich_valid_inputs_produce_expected_argv(tmp_path: Path) -> None:
    env = {
        "DATAJUD_TRIBUNAL_INPUT": "tjro",
        "DATAJUD_LIMITE_INPUT": "500",
        "DATAJUD_SKIP_UPLOAD_INPUT": "false",
    }
    result = _run_script(
        "datajud-enrich.yml", "enrich", "Enrich CNJs with DataJud metadata", env, tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        ["run", "--no-dev", "datajud", "enrich", "--tribunal", "tjro", "--limit", "500"]
    ]


def test_datajud_enrich_skip_upload_appends_flag(tmp_path: Path) -> None:
    env = {
        "DATAJUD_TRIBUNAL_INPUT": "stj",
        "DATAJUD_LIMITE_INPUT": "10",
        "DATAJUD_SKIP_UPLOAD_INPUT": "true",
    }
    result = _run_script(
        "datajud-enrich.yml", "enrich", "Enrich CNJs with DataJud metadata", env, tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "--no-dev",
            "datajud",
            "enrich",
            "--tribunal",
            "stj",
            "--limit",
            "10",
            "--skip-upload",
        ]
    ]


# ---------------------------------------------------------------------------
# bootstrap-corpus.yml — "Download texts from IA" / "Run OPF + heuristic (Stage 1)"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "step_name",
    ["Download texts from IA", "Run OPF + heuristic (Stage 1)"],
)
def test_bootstrap_corpus_has_no_spliced_inputs(step_name: str) -> None:
    _assert_no_dispatch_splice_or_eval("bootstrap-corpus.yml", "stage1-opf-heuristic", step_name)


def test_bootstrap_corpus_download_rejects_non_integer(tmp_path: Path) -> None:
    env = {
        "BOOTSTRAP_TARGET": "500; touch pwned",
        "BOOTSTRAP_N_ITEMS": "10",
        "BOOTSTRAP_MAX_PER_TRIBUNAL": "100",
    }
    result = _run_script(
        "bootstrap-corpus.yml", "stage1-opf-heuristic", "Download texts from IA", env, tmp_path
    )
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]
    assert not (tmp_path / "pwned").exists()


def test_bootstrap_corpus_download_valid_inputs_produce_expected_argv(tmp_path: Path) -> None:
    env = {
        "BOOTSTRAP_TARGET": "500",
        "BOOTSTRAP_N_ITEMS": "10",
        "BOOTSTRAP_MAX_PER_TRIBUNAL": "100",
    }
    result = _run_script(
        "bootstrap-corpus.yml", "stage1-opf-heuristic", "Download texts from IA", env, tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "python",
            "scripts/augment_segmenter_data.py",
            "--target",
            "500",
            "--max-per-tribunal",
            "100",
            "--output-dir",
            "data/bootstrap_texts",
            "--n-items",
            "10",
        ]
    ]


def test_bootstrap_corpus_stage1_valid_input_produces_expected_argv(tmp_path: Path) -> None:
    env = {"BOOTSTRAP_TARGET": "500"}
    result = _run_script(
        "bootstrap-corpus.yml",
        "stage1-opf-heuristic",
        "Run OPF + heuristic (Stage 1)",
        env,
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "--no-sync",
            "python",
            "scripts/bootstrap_training_corpus.py",
            "--input",
            "data/bootstrap_texts/train.jsonl",
            "--target",
            "500",
            "--device",
            "-1",
            "--save-intermediate",
            "data/intermediate.jsonl",
        ]
    ]


# ---------------------------------------------------------------------------
# collect-zips.yml — "Run djen-backup"
# ---------------------------------------------------------------------------


def test_collect_zips_has_no_eval_or_spliced_inputs() -> None:
    _assert_no_dispatch_splice_or_eval("collect-zips.yml", "collect", "Run djen-backup")


@pytest.mark.parametrize(
    "env_overrides",
    [
        {"COLLECT_WORKERS": "8; touch pwned"},
        {"COLLECT_TRIBUNAL": "TJSP; touch pwned"},
        {"COLLECT_START_DATE": "2020-01-01`touch pwned`"},
        {"COLLECT_END_DATE": "$(touch pwned)"},
    ],
)
def test_collect_zips_rejects_malicious_inputs(
    env_overrides: dict[str, str], tmp_path: Path
) -> None:
    env = {
        "COLLECT_WORKERS": "8",
        "COLLECT_DEADLINE_MINUTES": "17",
        "COLLECT_TRIBUNAL": "",
        "COLLECT_START_DATE": "2020-01-01",
        "COLLECT_END_DATE": "",
        **env_overrides,
    }
    result = _run_script("collect-zips.yml", "collect", "Run djen-backup", env, tmp_path)
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]
    assert not (tmp_path / "pwned").exists()


def test_collect_zips_valid_inputs_produce_expected_argv(tmp_path: Path) -> None:
    env = {
        "COLLECT_WORKERS": "8",
        "COLLECT_DEADLINE_MINUTES": "17",
        "COLLECT_TRIBUNAL": "",
        "COLLECT_START_DATE": "2020-01-01",
        "COLLECT_END_DATE": "",
    }
    result = _run_script("collect-zips.yml", "collect", "Run djen-backup", env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "--no-dev",
            "djen-backup",
            "--deadline-minutes",
            "17",
            "--workers",
            "8",
            "--start-date",
            "2020-01-01",
            "--use-proxy",
            "--no-fail-fast",
        ]
    ]


def test_collect_zips_tribunal_and_end_date_append_flags(tmp_path: Path) -> None:
    env = {
        "COLLECT_WORKERS": "4",
        "COLLECT_DEADLINE_MINUTES": "10",
        "COLLECT_TRIBUNAL": "TJSP",
        "COLLECT_START_DATE": "2020-01-01",
        "COLLECT_END_DATE": "2024-12-31",
    }
    result = _run_script("collect-zips.yml", "collect", "Run djen-backup", env, tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "--no-dev",
            "djen-backup",
            "--deadline-minutes",
            "10",
            "--workers",
            "4",
            "--start-date",
            "2020-01-01",
            "--use-proxy",
            "--no-fail-fast",
            "--end-date",
            "2024-12-31",
            "--tribunal",
            "TJSP",
        ]
    ]


# ---------------------------------------------------------------------------
# roundtrip-check.yml — "Run roundtrip equivalence check"
# ---------------------------------------------------------------------------


def test_roundtrip_check_has_no_spliced_inputs() -> None:
    _assert_no_dispatch_splice_or_eval(
        "roundtrip-check.yml", "roundtrip", "Run roundtrip equivalence check"
    )


@pytest.mark.parametrize(
    "env_overrides",
    [
        {"ROUNDTRIP_SAMPLE_SIZE": "50; touch pwned"},
        {"ROUNDTRIP_DATE": "2024-01-01`touch pwned`"},
    ],
)
def test_roundtrip_check_rejects_malicious_inputs(
    env_overrides: dict[str, str], tmp_path: Path
) -> None:
    env = {"ROUNDTRIP_DATE": "", "ROUNDTRIP_SAMPLE_SIZE": "50", **env_overrides}
    result = _run_script(
        "roundtrip-check.yml", "roundtrip", "Run roundtrip equivalence check", env, tmp_path
    )
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]
    assert not (tmp_path / "pwned").exists()


def test_roundtrip_check_valid_inputs_produce_expected_argv(tmp_path: Path) -> None:
    env = {"ROUNDTRIP_DATE": "2024-06-01", "ROUNDTRIP_SAMPLE_SIZE": "25"}
    result = _run_script(
        "roundtrip-check.yml", "roundtrip", "Run roundtrip equivalence check", env, tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "python",
            "scripts/roundtrip_check.py",
            "--sample",
            "25",
            "--date",
            "2024-06-01",
        ]
    ]


# ---------------------------------------------------------------------------
# sample-segmenter-texts.yml — "Sample texts for ..." (matrix step)
# ---------------------------------------------------------------------------


def test_sample_segmenter_texts_has_no_spliced_dispatch_inputs() -> None:
    script = _step(
        "sample-segmenter-texts.yml",
        "sample",
        "Sample texts for ${{ matrix.tribunal }} (${{ matrix.mode }})",
    )["run"]
    assert "eval" not in script
    assert "${{ inputs." not in script
    assert "${{ github.event.inputs." not in script


@pytest.mark.parametrize(
    "env_overrides",
    [
        {"SAMPLE_N_PER_TRIBUNAL": "20; touch pwned"},
        {"SAMPLE_MAX_ZIPS": "10`touch pwned`"},
        {"SAMPLE_SEED": "$(touch pwned)"},
    ],
)
def test_sample_segmenter_texts_rejects_malicious_inputs(
    env_overrides: dict[str, str], tmp_path: Path
) -> None:
    env = {
        "SAMPLE_N_PER_TRIBUNAL": "20",
        "SAMPLE_MAX_ZIPS": "10",
        "SAMPLE_SEED": "42",
        **env_overrides,
    }
    result = _run_script(
        "sample-segmenter-texts.yml",
        "sample",
        "Sample texts for ${{ matrix.tribunal }} (${{ matrix.mode }})",
        env,
        tmp_path,
        matrix={"tribunal": "TJSP", "mode": "sentenca"},
    )
    assert result.returncode != 0
    assert result.argv_calls == []  # type: ignore[attr-defined]
    assert not (tmp_path / "pwned").exists()


def test_sample_segmenter_texts_valid_inputs_produce_expected_argv(tmp_path: Path) -> None:
    env = {"SAMPLE_N_PER_TRIBUNAL": "20", "SAMPLE_MAX_ZIPS": "10", "SAMPLE_SEED": "42"}
    result = _run_script(
        "sample-segmenter-texts.yml",
        "sample",
        "Sample texts for ${{ matrix.tribunal }} (${{ matrix.mode }})",
        env,
        tmp_path,
        matrix={"tribunal": "TJSP", "mode": "sentenca"},
    )
    assert result.returncode == 0, result.stderr
    assert result.argv_calls == [  # type: ignore[attr-defined]
        [
            "run",
            "python",
            "scripts/sample_ia_texts.py",
            "--tribunal",
            "TJSP",
            "--mode",
            "sentenca",
            "--n",
            "20",
            "--max-zips",
            "10",
            "--seed",
            "42",
            "--output-dir",
            "/tmp/segmenter_samples",
        ]
    ]
