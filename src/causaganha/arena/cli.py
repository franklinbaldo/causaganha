"""Offline arena commands for the CausaGanha Lab."""

from __future__ import annotations

import json
from pathlib import Path

from cyclopts import App

from causaganha.arena.formal import (
    FormalCase,
    Narrative,
    audit_narrative,
    lean_source,
    narrative_request,
    verify,
)
from causaganha.arena.search import Predictions, sample
from causaganha.arena.league import replay
from causaganha.arena.models import Season

app = App(name="arena", help="Lab: carreira competitiva de modelos, sem chamadas de API.")


@app.command
def avaliar(temporada: Path) -> None:
    """Valide e reproduza uma temporada JSON; imprima o placar auditável em JSON."""
    season = Season.model_validate_json(temporada.read_text(encoding="utf-8"))
    print(json.dumps(replay(season), ensure_ascii=False, indent=2, allow_nan=False))


@app.command
def contrato() -> None:
    """Exiba o JSON Schema de temporadas, peças, votos e âncoras."""
    print(json.dumps(Season.model_json_schema(), ensure_ascii=False, indent=2, allow_nan=False))


def _formal(path: Path) -> FormalCase:
    return FormalCase.model_validate_json(path.read_text(encoding="utf-8"))


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


@app.command
def formalizar(caso: Path) -> None:
    """Exporte fatos e conclusão para Lean, sem afirmar que já foram verificados."""
    print(lean_source(_formal(caso)), end="")


@app.command
def verificar_formal(caso: Path, *, lean: str = "lean") -> None:
    """Compile o caso no Lean e exija provas sem dependências axiomáticas."""
    _json(verify(_formal(caso), lean=lean))


@app.command
def preparar_narrativa(caso: Path) -> None:
    """Prepare os fatos para o narrador, omitindo a conclusão formal privada."""
    _json(narrative_request(_formal(caso)))


@app.command
def auditar_narrativa(caso: Path, narrativa: Path) -> None:
    """Confira versão e cobertura de IDs; fidelidade semântica exige revisão."""
    text = Narrative.model_validate_json(narrativa.read_text(encoding="utf-8"))
    _json(audit_narrative(_formal(caso), text))


@app.command
def explorar(
    caso: Path, previsoes: Path, *, steps: int = 100, beta: float = 5.0, seed: int = 0
) -> None:
    """Explore fatos por MCMC usando previsões importadas, sem executar modelos."""
    case = _formal(caso)
    predictions = Predictions.model_validate_json(previsoes.read_text(encoding="utf-8"))
    trace = sample(case, predictions.predictor(case), steps=steps, beta=beta, seed=seed)
    best = max(trace, key=lambda row: row["difficulty"])
    candidate = case.model_dump(mode="json")
    candidate["assignment"] = best["assignment"]
    _json(
        {
            "seed": seed,
            "beta": beta,
            "demonstration": predictions.demonstration,
            "models": predictions.models,
            "lean_verified": False,
            "target": "uniform_admissible_times_exp_beta_disagreement",
            "best_candidate": candidate,
            "trace": trace,
        }
    )


if __name__ == "__main__":
    app()
