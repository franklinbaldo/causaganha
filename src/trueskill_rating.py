# Este arquivo conterá a lógica para cálculos de rating usando TrueSkill.
# Serão implementadas funções para inicializar e atualizar ratings.
from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Tuple
import logging

import toml
import trueskill

logger = logging.getLogger(__name__)


# Possíveis resultados de uma partida de TrueSkill
class MatchResult(Enum):
    """Representa o desfecho de uma partida para atualização de ratings."""

    WIN_A = "win_a"
    WIN_B = "win_b"
    DRAW = "draw"


# Valores padrao para o ambiente TrueSkill
_DEFAULT_CONFIG = {
    "mu": 25.0,
    "sigma": 25.0 / 3,
    "beta": (25.0 / 3) / 2,
    "tau": (25.0 / 3) / 100,
    "draw_probability": 0.10,
    "backend": None,
}

# Carrega configurações do arquivo config.toml
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.toml"


def load_trueskill_config() -> Dict[str, Any]:
    """Carrega as configurações do TrueSkill do arquivo config.toml."""
    try:
        config = toml.load(CONFIG_PATH)
        return config.get("trueskill", _DEFAULT_CONFIG)
    except FileNotFoundError as exc:
        # Fallback para valores padrão se config.toml não for encontrado
        logger.error("config.toml not found at %s: %s", CONFIG_PATH, exc)
        return _DEFAULT_CONFIG
    except (KeyError, ValueError, TypeError) as exc:
        # Em caso de erro ao ler o toml, usa os padrões e loga o erro
        logger.error("Failed to load TrueSkill config: %s", exc)
        return _DEFAULT_CONFIG


TS_CONFIG = load_trueskill_config()

# Inicializa o ambiente TrueSkill com base nas configurações carregadas
ENV = trueskill.TrueSkill(
    mu=TS_CONFIG.get("mu", 25.0),
    sigma=TS_CONFIG.get("sigma", 25.0 / 3),
    beta=TS_CONFIG.get("beta", (25.0 / 3) / 2),
    tau=TS_CONFIG.get("tau", (25.0 / 3) / 100),
    draw_probability=TS_CONFIG.get("draw_probability", 0.10),
    backend=TS_CONFIG.get("backend", None),  # Permite especificar 'mpmath' ou 'scipy'
)


def create_new_rating() -> trueskill.Rating:
    """Cria um novo objeto de rating TrueSkill com os valores padrão do ambiente."""
    return ENV.create_rating()


def update_ratings(
    env: trueskill.TrueSkill,
    team_ratings_a: list[trueskill.Rating],
    team_ratings_b: list[trueskill.Rating],
    result: MatchResult,
) -> Tuple[list[trueskill.Rating], list[trueskill.Rating]]:
    """
    Atualiza os ratings TrueSkill para duas equipes com base no resultado da partida.

    Args:
        team_ratings_a: Lista de objetos Rating para a equipe A.
        team_ratings_b: Lista de objetos Rating para a equipe B.
        result: Resultado da partida (:class:`MatchResult`).

    Returns:
        Uma tupla contendo duas listas:
        - Novos ratings para os membros da equipe A.
        - Novos ratings para os membros da equipe B.

    Raises:
        ValueError: Se o resultado fornecido for inválido.
    """
    if result == MatchResult.WIN_A:
        ranks = [0, 1]  # Posição 0 para o vencedor, 1 para o perdedor
    elif result == MatchResult.WIN_B:
        ranks = [1, 0]
    elif result == MatchResult.DRAW:
        ranks = [0, 0]  # Mesma posição para empate
    else:
        raise ValueError(
            f"Resultado desconhecido: {result}. Use 'win_a', 'win_b', ou 'draw'."
        )

    new_team_a_ratings, new_team_b_ratings = env.rate(
        [team_ratings_a, team_ratings_b], ranks=ranks
    )
    return new_team_a_ratings, new_team_b_ratings
