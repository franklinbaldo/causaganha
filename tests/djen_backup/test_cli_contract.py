"""Congela o contrato de CLI de `djen-backup` antes da migração Typer→Cyclopts (RFC 0013).

`Command.make_context` só faz o parsing do argv — nunca invoca o callback.
Sem rede, sem I/O, sem executar `run_sync`/`drain`. É por isso que estes
testes conseguem reproduzir o argv exato dos workflows (`collect-zips.yml`,
`upload-backlog.yml`) sem depender de DJEN nem do Internet Archive.

Se a migração para Cyclopts mudar o nome, o default ou a negação de uma
flag, o parsing continua "funcionando" — só que com um valor diferente. É
exatamente isso que os asserts abaixo travam.
"""

from __future__ import annotations

from datetime import date, timedelta

from typer.main import get_command

from djen_backup.__main__ import app


_CMD = get_command(app)


def test_subcommands_presentes() -> None:
    assert set(_CMD.commands) == {"check", "upload", "drain", "probe", "reset"}


def test_collect_zips_argv_bare_callback() -> None:
    """Reproduz o argv de `.github/workflows/collect-zips.yml` sem `--end-date`/`--tribunal`.

    O callback usa `invoke_without_command=True` — Cyclopts não tem esse
    padrão; a Fase 4 precisa de um `default_command` explícito que aceite
    este mesmo argv e produza o mesmo `ctx.params`.
    """
    argv = [
        "--deadline-minutes",
        "17",
        "--workers",
        "8",
        "--start-date",
        "2020-01-01",
        "--use-proxy",
        "--no-fail-fast",
    ]
    ctx = _CMD.make_context("djen-backup", list(argv))

    expected_end_date = (date.today() - timedelta(days=1)).isoformat()
    assert ctx.invoked_subcommand is None
    assert ctx.params == {
        "start_date": "2020-01-01",
        "end_date": expected_end_date,
        "tribunal": None,
        "deadline_minutes": 17,
        "max_items": 0,
        "workers": 8,
        "fail_fast": False,  # <- é isto que --no-fail-fast precisa continuar produzindo
        "use_proxy": True,
    }


def test_collect_zips_argv_com_tribunal_e_end_date() -> None:
    """Variante do workflow quando `end_date`/`tribunal` vêm de `workflow_dispatch`."""
    argv = [
        "--deadline-minutes",
        "17",
        "--workers",
        "8",
        "--start-date",
        "2020-01-01",
        "--use-proxy",
        "--no-fail-fast",
        "--end-date",
        "2026-07-20",
        "--tribunal",
        "TJSP",
    ]
    ctx = _CMD.make_context("djen-backup", list(argv))

    assert ctx.params["tribunal"] == "TJSP"
    assert ctx.params["end_date"] == "2026-07-20"
    assert ctx.params["fail_fast"] is False


def test_fail_fast_e_negavel_via_no_fail_fast() -> None:
    """`fail_fast` é `typer.Option(True, ...)` sem string explícita — Typer gera
    o par `--fail-fast/--no-fail-fast` automaticamente. Cyclopts precisa
    reproduzir os DOIS nomes, não só aceitar `--fail-fast=false`.
    """
    (param,) = [p for p in _CMD.params if p.name == "fail_fast"]
    assert param.opts == ["--fail-fast"]
    assert param.secondary_opts == ["--no-fail-fast"]
    assert param.default is True


def test_use_proxy_do_callback_bare_tambem_e_negavel() -> None:
    """Ao contrário do `use_proxy` de `drain` (ver `test_drain_use_proxy_nao_e_negavel`),
    o do callback bare usa `typer.Option(False, ...)` sem string explícita —
    Typer também gera `--no-use-proxy` aqui. As duas declarações no mesmo
    arquivo divergem por causa de um detalhe fácil de apagar numa migração
    mecânica: uma passa `"--use-proxy"` explicitamente, a outra não.
    """
    (param,) = [p for p in _CMD.params if p.name == "use_proxy"]
    assert param.opts == ["--use-proxy"]
    assert param.secondary_opts == ["--no-use-proxy"]


def test_workers_do_callback_tem_default_computado_no_import() -> None:
    """`DEFAULT_WORKERS = load_djen_safe_concurrency()` roda no import do módulo —
    o default depende da máquina, então não fixamos o valor aqui, só o tipo.
    Candidato a corrigir na Fase 2 (side effect de import) antes de expor
    como tool MCP: um servidor MCP não deveria calcular isso no boot.
    """
    (param,) = [p for p in _CMD.params if p.name == "workers"]
    assert param.type.name == "int"
    assert isinstance(param.default, int)
    assert param.default > 0


def test_upload_backlog_argv_drain() -> None:
    """Reproduz o argv exato de `.github/workflows/upload-backlog.yml`."""
    drain = _CMD.commands["drain"]
    argv = [
        "--workers",
        "24",
        "--batch-size",
        "200",
        "--deadline-minutes",
        "55",
        "--use-proxy",
    ]
    ctx = drain.make_context("drain", list(argv))

    assert ctx.params == {
        "workers": 24,
        "batch_size": 200,
        "deadline_minutes": 55,
        "use_proxy": True,
    }


def test_drain_use_proxy_nao_e_negavel() -> None:
    """`drain` passa `"--use-proxy"` explicitamente a `typer.Option` — isso
    SUPRIME a geração automática de `--no-use-proxy` que existe no callback
    bare. Mesmo nome de parâmetro, comportamento diferente dentro do mesmo
    arquivo: é exatamente o tipo de detalhe que uma migração mecânica apaga
    sem notar.
    """
    drain = _CMD.commands["drain"]
    (param,) = [p for p in drain.params if p.name == "use_proxy"]
    assert param.opts == ["--use-proxy"]
    assert param.secondary_opts == []
    assert param.default is False


def test_drain_defaults_sao_literais_fixos() -> None:
    """Ao contrário do callback bare, os defaults de `drain` são literais no
    código-fonte — seguro fixar aqui (nada computado em import time).
    """
    drain = _CMD.commands["drain"]
    defaults = {p.name: p.default for p in drain.params}
    assert defaults == {
        "workers": 6,
        "batch_size": 100,
        "deadline_minutes": 14,
        "use_proxy": False,
    }
