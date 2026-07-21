"""Congela o contrato de CLI de `stj-acordaos` antes da migração Typer→Cyclopts (RFC 0013).

Ver `tests/djen_backup/test_cli_contract.py` para a explicação do método:
`Command.make_context` só faz parsing, nunca invoca o callback — sem rede,
sem I/O, sem download de verdade.
"""

from __future__ import annotations

from pathlib import Path

from typer.main import get_command

from stj_acordaos.__main__ import app


_CMD = get_command(app)


def test_subcommands_presentes() -> None:
    assert set(_CMD.commands) == {"download", "upload", "status"}


def test_stj_sync_argv_download() -> None:
    """Reproduz `stj-sync.yml`: `stj-acordaos download --data-dir ... --manifest-path ...`."""
    download = _CMD.commands["download"]
    argv = [
        "--data-dir",
        "data/stj",
        "--manifest-path",
        "data/stj/stj-manifest.csv",
    ]
    ctx = download.make_context("download", list(argv))

    assert ctx.params == {
        "data_dir": "data/stj",
        "manifest_path": "data/stj/stj-manifest.csv",
    }


def test_stj_sync_argv_upload() -> None:
    """Reproduz `stj-sync.yml`: `stj-acordaos upload --data-dir ... --manifest-path ...`.

    O workflow não passa `--parquet-path` no argv — `parquet_path` fica no
    default computado a partir de `data_dir` default (não do `--data-dir`
    informado: são opções independentes, não há recomputação). Desde a Fase
    2 do RFC 0013, `ia_key`/`ia_secret` não são mais parâmetros de CLI (ver
    `test_upload_nao_tem_mais_credenciais_ia_como_opcao_de_cli`) — as
    credenciais vêm só de `IA_ACCESS_KEY`/`IA_SECRET_KEY` no ambiente,
    lidas dentro de `stj_acordaos.service.ia_credentials()`, injetadas pelo
    workflow via `env:` do step.
    """
    upload = _CMD.commands["upload"]
    argv = [
        "--data-dir",
        "data/stj",
        "--manifest-path",
        "data/stj/stj-manifest.csv",
    ]
    ctx = upload.make_context("upload", list(argv))

    assert ctx.params == {
        "data_dir": "data/stj",
        "manifest_path": "data/stj/stj-manifest.csv",
        "parquet_path": Path("data/stj/stj-acordaos.parquet"),
    }


def test_stj_sync_argv_status() -> None:
    """Reproduz `stj-sync.yml`: `stj-acordaos status --manifest-path ...`."""
    status = _CMD.commands["status"]
    ctx = status.make_context("status", ["--manifest-path", "data/stj/stj-manifest.csv"])

    assert ctx.params == {"manifest_path": "data/stj/stj-manifest.csv"}


def test_upload_nao_tem_mais_credenciais_ia_como_opcao_de_cli() -> None:
    """Fase 2 do RFC 0013: `ia_key`/`ia_secret` deixaram de ser opção de CLI.

    Antes eram `typer.Option(envvar=...)` — a credencial do Internet Archive
    era literalmente um parâmetro de CLI, o que teria virado campo de schema
    numa tool MCP. Agora `upload` só lê `IA_ACCESS_KEY`/`IA_SECRET_KEY` do
    ambiente via `stj_acordaos.service.ia_credentials()` — nada aparece em
    `--help` nem em `ctx.params`.
    """
    upload = _CMD.commands["upload"]
    by_name = {p.name: p for p in upload.params}
    assert "ia_key" not in by_name
    assert "ia_secret" not in by_name


def test_download_e_status_tem_defaults_de_path_fixos() -> None:
    """Defaults de `download`/`status` são caminhos literais no código-fonte —
    seguro comparar por igualdade de `Path`, independente do SO em que o
    teste roda (Windows aqui, `ubuntu-latest` no CI).
    """
    download = _CMD.commands["download"]
    by_name = {p.name: p for p in download.params}
    assert by_name["data_dir"].default == Path("data/stj")
    assert by_name["manifest_path"].default == Path("data/stj/stj-manifest.csv")
