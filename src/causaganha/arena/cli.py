"""Offline arena commands for the CausaGanha Lab."""

from __future__ import annotations

import json
from pathlib import Path

from cyclopts import App

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


if __name__ == "__main__":
    app()
