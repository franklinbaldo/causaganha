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


def test_stj_sync_argv_upload(monkeypatch) -> None:
    """Reproduz `stj-sync.yml`: `stj-acordaos upload --data-dir ... --manifest-path ...`.

    O workflow não passa `--parquet-path`/`--ia-key`/`--ia-secret` no argv —
    `parquet_path` fica no default computado a partir de `data_dir` default
    (não do `--data-dir` informado: são opções independentes, não há
    recomputação), e as credenciais vêm só de env (`IA_ACCESS_KEY`/
    `IA_SECRET_KEY`, injetadas pelo workflow via `env:` do step).

    `ia_key`/`ia_secret` usam `envvar=...`, e `Command.make_context` lê essas
    variáveis do processo de verdade — `monkeypatch.setenv` com valores
    sentinela reproduz a injeção do workflow e confirma que elas chegam a
    `ctx.params`, em vez de assumir que ficam vazias (isso só valia por
    acidente, porque o job de CI não tinha essas variáveis no ambiente; numa
    máquina com `IA_ACCESS_KEY`/`IA_SECRET_KEY` exportadas, o teste antigo
    quebrava).
    """
    monkeypatch.setenv("IA_ACCESS_KEY", "sentinel-ia-key")
    monkeypatch.setenv("IA_SECRET_KEY", "sentinel-ia-secret")

    upload = _CMD.commands["upload"]
    argv = [
        "--data-dir",
        "data/stj",
        "--manifest-path",
        "data/stj/stj-manifest.csv",
    ]
    ctx = upload.make_context("upload", list(argv))

    assert ctx.params["data_dir"] == "data/stj"
    assert ctx.params["manifest_path"] == "data/stj/stj-manifest.csv"
    assert ctx.params["ia_key"] == "sentinel-ia-key"
    assert ctx.params["ia_secret"] == "sentinel-ia-secret"  # noqa: S105 — test fixture, not a real credential


def test_stj_sync_argv_status() -> None:
    """Reproduz `stj-sync.yml`: `stj-acordaos status --manifest-path ...`."""
    status = _CMD.commands["status"]
    ctx = status.make_context("status", ["--manifest-path", "data/stj/stj-manifest.csv"])

    assert ctx.params == {"manifest_path": "data/stj/stj-manifest.csv"}


def test_upload_credenciais_ia_sao_opcao_de_cli_com_envvar() -> None:
    """`ia_key`/`ia_secret` são `typer.Option(envvar=...)` — a credencial do
    Internet Archive é literalmente um parâmetro de CLI. Isso é o que a Fase
    2 do RFC 0013 precisa eliminar antes de qualquer coisa virar tool MCP:
    um schema de tool não pode ter campo de credencial.
    """
    upload = _CMD.commands["upload"]
    by_name = {p.name: p for p in upload.params}
    assert by_name["ia_key"].envvar == "IA_ACCESS_KEY"
    assert by_name["ia_secret"].envvar == "IA_SECRET_KEY"


def test_download_e_status_tem_defaults_de_path_fixos() -> None:
    """Defaults de `download`/`status` são caminhos literais no código-fonte —
    seguro comparar por igualdade de `Path`, independente do SO em que o
    teste roda (Windows aqui, `ubuntu-latest` no CI).
    """
    download = _CMD.commands["download"]
    by_name = {p.name: p for p in download.params}
    assert by_name["data_dir"].default == Path("data/stj")
    assert by_name["manifest_path"].default == Path("data/stj/stj-manifest.csv")
