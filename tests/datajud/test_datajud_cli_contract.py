"""Congela o contrato de CLI de `datajud` antes da migração Typer→Cyclopts (RFC 0013).

Ver `tests/djen_backup/test_cli_contract.py` para a explicação do método:
`Command.make_context` só faz parsing, nunca invoca o callback — sem rede,
sem I/O, sem consultar o DataJud de verdade.
"""

from __future__ import annotations

from pathlib import Path

from typer.main import get_command

from datajud.__main__ import app


_CMD = get_command(app)


def test_subcommands_presentes() -> None:
    assert {"enrich", "facetas", "status"} <= set(_CMD.commands)


def test_datajud_enrich_argv_com_defaults_do_workflow() -> None:
    """Reproduz `datajud-enrich.yml`: `${TRIBUNAL:-tjro}` e `${LIMITE:-500}`
    são os valores efetivos quando o job roda por `schedule` (sem
    `workflow_dispatch` informando os inputs).
    """
    enrich = _CMD.commands["enrich"]
    ctx = enrich.make_context("enrich", ["--tribunal", "tjro", "--limit", "500"])

    assert ctx.params["tribunal"] == "tjro"
    assert ctx.params["limit"] == 500
    assert ctx.params["skip_upload"] is False
    assert ctx.params["cnj"] == ()
    assert ctx.params["data_dir"] == Path("data/datajud")
    assert ctx.params["sources_dir"] == Path("data")


def test_datajud_enrich_argv_com_skip_upload() -> None:
    """Variante de `datajud-enrich.yml` quando `workflow_dispatch` informa `skip_upload: true`."""
    enrich = _CMD.commands["enrich"]
    ctx = enrich.make_context("enrich", ["--tribunal", "tjro", "--limit", "500", "--skip-upload"])

    assert ctx.params["skip_upload"] is True


def test_skip_upload_nao_e_negavel() -> None:
    """`skip_upload` passa `"--skip-upload"` explicitamente a `typer.Option` —
    não há `--no-skip-upload` gerado. Mesmo padrão de `drain`'s `use_proxy`
    em `djen_backup` (ver `tests/djen_backup/test_cli_contract.py`).
    """
    enrich = _CMD.commands["enrich"]
    (param,) = [p for p in enrich.params if p.name == "skip_upload"]
    assert param.opts == ["--skip-upload"]
    assert param.secondary_opts == []
    assert param.default is False


def test_cnj_e_repetivel() -> None:
    """`--cnj` é `list[str] | None` — repetível, um CNJ explícito por ocorrência."""
    enrich = _CMD.commands["enrich"]
    (param,) = [p for p in enrich.params if p.name == "cnj"]
    assert param.multiple is True


def test_datajud_status_argv() -> None:
    """Reproduz `datajud-enrich.yml`: `datajud status --data-dir data/datajud`.

    Quando `--data-dir` é informado no argv, o Click converte a string via o
    `Path` type (devolve `str`); é só o *default* não-informado que fica como
    o objeto `Path` cru (ver `test_datajud_enrich_argv_com_defaults_do_workflow`,
    onde nem `data_dir` nem `sources_dir` são passados no argv).
    """
    status = _CMD.commands["status"]
    ctx = status.make_context("status", ["--data-dir", "data/datajud"])

    assert ctx.params == {"data_dir": "data/datajud"}


def test_enrich_nao_tem_mais_credenciais_ia_como_opcao_de_cli() -> None:
    """Fase 2 do RFC 0013: `ia_key`/`ia_secret` deixaram de ser opção de CLI.

    Antes eram `typer.Option(envvar=...)`, mesmo padrão de `stj_acordaos`.
    Agora `enrich` só lê `IA_ACCESS_KEY`/`IA_SECRET_KEY` do ambiente via
    `datajud.service.ia_credentials()` — nada aparece em `--help` nem em
    `ctx.params`, então nada disso vira campo de schema numa tool MCP.
    """
    enrich = _CMD.commands["enrich"]
    by_name = {p.name: p for p in enrich.params}
    assert "ia_key" not in by_name
    assert "ia_secret" not in by_name
