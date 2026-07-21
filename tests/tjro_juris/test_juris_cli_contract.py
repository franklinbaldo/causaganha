"""Congela o contrato de CLI de `tjro-juris` antes da migração Typer→Cyclopts (RFC 0013).

Ver `tests/djen_backup/test_cli_contract.py` para a explicação do método:
`Command.make_context` só faz parsing, nunca invoca o callback — sem rede,
sem I/O, sem crawl de verdade.
"""

from __future__ import annotations

from typer.main import get_command

from tjro_juris.__main__ import app


_CMD = get_command(app)


def test_subcommands_presentes() -> None:
    """`consolidate` também existe mas não é chamado por nenhum workflow — não
    faz parte da superfície de risco desta RFC, por isso o teste checa
    presença (`<=`), não igualdade exata.
    """
    assert {"crawl", "upload", "status"} <= set(_CMD.commands)


def test_tjro_sync_argv_crawl_incremental() -> None:
    """Reproduz `tjro-sync.yml` no modo `--mes` — variante de execução manual via
    `workflow_dispatch` (`tjro_mes`), não o caso comum de cron. O cron diário
    roda sem inputs e força `--desde-ano 1988` (ver
    `test_tjro_sync_argv_crawl_backfill_historico`), continuando o backfill
    histórico em vez de crawlear só o mês corrente.
    """
    crawl = _CMD.commands["crawl"]
    argv = ["data/tjro-juris", "--mes", "2026-07"]
    ctx = crawl.make_context("crawl", list(argv))

    assert ctx.params == {
        "data_dir": "data/tjro-juris",
        "tipo": (),
        "ano": None,
        "mes": "2026-07",
        "desde_ano": None,
    }


def test_tjro_sync_argv_crawl_backfill_historico() -> None:
    """Reproduz `tjro-sync.yml` fora de `workflow_dispatch` — o workflow força
    `--desde-ano 1988` quando nenhum dos três filtros de data é informado.
    """
    crawl = _CMD.commands["crawl"]
    argv = ["data/tjro-juris", "--desde-ano", "1988"]
    ctx = crawl.make_context("crawl", list(argv))

    assert ctx.params["desde_ano"] == 1988
    assert ctx.params["ano"] is None
    assert ctx.params["mes"] is None


def test_tjro_sync_argv_crawl_com_tipos_repetidos() -> None:
    """`--tipo` é repetível — o workflow itera uma lista separada por vírgula
    e monta `--tipo "$t"` uma vez por item (`tjro-sync.yml`).
    """
    crawl = _CMD.commands["crawl"]
    argv = ["data/tjro-juris", "--tipo", "acordao", "--tipo", "sumula"]
    ctx = crawl.make_context("crawl", list(argv))

    assert ctx.params["tipo"] == ("acordao", "sumula")


def test_crawl_data_dir_e_argumento_posicional() -> None:
    """`data_dir` é `typer.Argument`, não uma opção — o workflow monta
    `tjro-juris crawl data/tjro-juris` sem flag. Cyclopts trata posicional
    diferente de opção; confirmar que isso sobrevive à migração.
    """
    crawl = _CMD.commands["crawl"]
    (param,) = [p for p in crawl.params if p.name == "data_dir"]
    assert param.param_type_name == "argument"


def test_tjro_sync_argv_upload() -> None:
    """Reproduz `tjro-juris upload data/tjro-juris` de `tjro-sync.yml`."""
    upload = _CMD.commands["upload"]
    ctx = upload.make_context("upload", ["data/tjro-juris"])

    assert ctx.params == {"data_dir": "data/tjro-juris"}


def test_tjro_sync_argv_status() -> None:
    """Reproduz `tjro-juris status data/tjro-juris` de `tjro-sync.yml`."""
    status = _CMD.commands["status"]
    ctx = status.make_context("status", ["data/tjro-juris"])

    assert ctx.params == {"data_dir": "data/tjro-juris"}
