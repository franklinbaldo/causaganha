"""Contract coverage for the Cyclopts-based segmenter-dataset CLI (RFC 0013 Fase 5).

Before this migration, no test in the repository imported
`segmenter_dataset.__main__` at all -- exactly the "no test ever imports
this module" hazard that let `causaganha.consolidate.cli` silently break
at import time (see the corresponding wiki pattern and PR #1350). This
file guards the argv contract Typer→Cyclopts migration must preserve:
required options, `exists=True`/`file_okay=False` path validation, and
the `min=`-equivalent numeric floor on `--iaa-resamples`.
"""

from __future__ import annotations

from tests.cli_contract.harness import _invoke


def test_segmenter_dataset_cli_module_imports() -> None:
    import segmenter_dataset.__main__  # noqa: F401


def test_empty_invocation_shows_help() -> None:
    """This CLI made a clean break from the old Typer app's `no_args_is_help`
    exit-2 convention: a bare invocation just shows help and exits 0,
    Cyclopts' own default -- there is no production workflow depending on
    the old exit code, so there is nothing to preserve here."""
    from segmenter_dataset.__main__ import app

    exit_code, output = _invoke(app, [])

    assert exit_code == 0, output
    assert "Usage:" in output


def test_assign_splits_help_builds() -> None:
    from segmenter_dataset.__main__ import app

    exit_code, output = _invoke(app, ["assign-splits", "--help"])

    assert exit_code == 0, output


def test_assign_splits_missing_required_option_is_a_usage_error() -> None:
    """Cyclopts' parse-error exit code (1) differs from Click/Typer's (2) --
    a documented framework difference (RFC 0013 Fase 4), not a regression."""
    from segmenter_dataset.__main__ import app

    exit_code, _ = _invoke(app, ["assign-splits"])

    assert exit_code == 1


def test_assign_splits_rejects_nonexistent_data_root(tmp_path) -> None:
    from segmenter_dataset.__main__ import app

    exit_code, output = _invoke(
        app,
        [
            "assign-splits",
            "--data-root",
            str(tmp_path / "does-not-exist"),
            "--output",
            str(tmp_path / "out.json"),
            "--seed",
            "1",
        ],
    )

    assert exit_code == 1, output


def test_assign_splits_rejects_data_root_that_is_a_file(tmp_path) -> None:
    """`file_okay=False` must survive the migration -- a file must be rejected
    even though it exists."""
    from segmenter_dataset.__main__ import app

    a_file = tmp_path / "not-a-dir"
    a_file.write_text("x", encoding="utf-8")

    exit_code, output = _invoke(
        app,
        [
            "assign-splits",
            "--data-root",
            str(a_file),
            "--output",
            str(tmp_path / "out.json"),
            "--seed",
            "1",
        ],
    )

    assert exit_code == 1, output


def test_build_release_help_builds() -> None:
    from segmenter_dataset.__main__ import app

    exit_code, output = _invoke(app, ["build-release", "--help"])

    assert exit_code == 0, output


def test_build_release_rejects_iaa_resamples_below_1000(tmp_path) -> None:
    from segmenter_dataset.__main__ import app

    manifest_path = tmp_path / "split_manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    label_space_path = tmp_path / "label_space.json"
    label_space_path.write_text("{}", encoding="utf-8")

    exit_code, output = _invoke(
        app,
        [
            "build-release",
            "--data-root",
            str(tmp_path),
            "--split-manifest",
            str(manifest_path),
            "--release-id",
            "r1",
            "--label-space",
            str(label_space_path),
            "--source-commit",
            "x" * 40,
            "--dependency-lock-hash",
            "x",
            "--ci-provider",
            "gh",
            "--ci-run-id",
            "1",
            "--guideline-version",
            "1",
            "--iaa-seed",
            "1",
            "--iaa-resamples",
            "1",
        ],
    )

    assert exit_code == 1, output


def test_render_dataset_card_help_builds() -> None:
    from segmenter_dataset.__main__ import app

    exit_code, output = _invoke(app, ["render-dataset-card", "--help"])

    assert exit_code == 0, output
