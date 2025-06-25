# Este arquivo conterá a lógica para cálculos de rating usando TrueSkill.
# Serão implementadas funções para inicializar e atualizar ratings.
import trueskill
import toml
from pathlib import Path
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Valores padrao para o ambiente TrueSkill
_DEFAULT_CONFIG = {
    "mu": 25.0,
    "sigma": 25.0 / 3,
    "beta": (25.0 / 3) / 2,
    "tau": (25.0 / 3) / 100,
    "draw_probability": 0.10,
    "backend": None,
}


class MatchResult(Enum):
    """Possible outcomes of a TrueSkill match."""

    WIN_A = "win_a"
    WIN_B = "win_b"
    DRAW = "draw"

# Carrega configurações do arquivo config.toml
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.toml"

def load_trueskill_config():
    """Carrega as configurações do TrueSkill do arquivo config.toml."""
    try:
        config = toml.load(CONFIG_PATH)
        return config.get("trueskill", _DEFAULT_CONFIG)
    except FileNotFoundError as exc:
        logger.error("config.toml not found at %s: %s", CONFIG_PATH, exc)
        return _DEFAULT_CONFIG
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Failed to load TrueSkill config: %s", exc)
        return _DEFAULT_CONFIG

TS_CONFIG = load_trueskill_config()

# Inicializa o ambiente TrueSkill com base nas configurações carregadas
ENV = trueskill.TrueSkill(
    mu=TS_CONFIG.get("mu", 25.0),
    sigma=TS_CONFIG.get("sigma", 25.0/3),
    beta=TS_CONFIG.get("beta", (25.0/3)/2),
    tau=TS_CONFIG.get("tau", (25.0/3)/100),
    draw_probability=TS_CONFIG.get("draw_probability", 0.10),
    backend=TS_CONFIG.get("backend", None) # Permite especificar 'mpmath' ou 'scipy'
)

def create_new_rating() -> trueskill.Rating:
    """Cria um novo objeto de rating TrueSkill com os valores padrão do ambiente."""
    return ENV.create_rating()

def update_ratings(
    env: trueskill.TrueSkill,
    team_ratings_a: list[trueskill.Rating],
    team_ratings_b: list[trueskill.Rating],
    result: MatchResult,
) -> tuple[list[trueskill.Rating], list[trueskill.Rating]]:
    """
    Atualiza os ratings TrueSkill para duas equipes com base no resultado da partida.

    Args:
        team_ratings_a: Lista de objetos Rating para a equipe A.
        team_ratings_b: Lista de objetos Rating para a equipe B.
        result: Um :class:`MatchResult` indicando o resultado da partida.

    Returns:
        Uma tupla contendo duas listas:
        - Novos ratings para os membros da equipe A.
        - Novos ratings para os membros da equipe B.

    Raises:
        ValueError: Se o resultado fornecido for inválido.
    """
    ranks_map = {
        MatchResult.WIN_A: [0, 1],
        MatchResult.WIN_B: [1, 0],
        MatchResult.DRAW: [0, 0],
    }
    try:
        ranks = ranks_map[result]
    except Exception as exc:  # KeyError or wrong type
        raise ValueError(
            f"Resultado desconhecido: {result}. Use MatchResult."
        ) from exc

    new_team_a_ratings, new_team_b_ratings = env.rate([team_ratings_a, team_ratings_b], ranks=ranks)
    return new_team_a_ratings, new_team_b_ratings

if __name__ == '__main__':
    # Demonstração simples de uso
    # Advogado 1 e 2 na Equipe A
    # Advogado 3 na Equipe B

    # Criar ratings iniciais para os advogados usando o ENV global
    # (que agora é carregado do config.toml ou usa defaults)
    adv1_rating = ENV.create_rating()
    adv2_rating = ENV.create_rating()
    adv3_rating = ENV.create_rating()
    # Para um advogado mais experiente, podemos ainda criar um rating customizado,
    # mas a sigma default virá do ENV.
    adv4_rating = trueskill.Rating(mu=30, sigma=ENV.sigma / 2)


    print(f"Usando configuração TrueSkill: Mu={ENV.mu}, Sigma={ENV.sigma}, Beta={ENV.beta}, Tau={ENV.tau}, DrawProb={ENV.draw_probability}")
    print(f"Rating inicial Adv1: mu={adv1_rating.mu:.2f}, sigma={adv1_rating.sigma:.2f}")
    print(f"Rating inicial Adv2: mu={adv2_rating.mu:.2f}, sigma={adv2_rating.sigma:.2f}")
    print(f"Rating inicial Adv3: mu={adv3_rating.mu:.2f}, sigma={adv3_rating.sigma:.2f}")
    print(f"Rating inicial Adv4 (Experiente): mu={adv4_rating.mu:.2f}, sigma={adv4_rating.sigma:.2f}\n")

    # Cenário 1: Equipe A (Adv1, Adv2) vence Equipe B (Adv3)
    team_a = [adv1_rating, adv2_rating]
    team_b = [adv3_rating]

    print("--- Cenário 1: Equipe A (Adv1, Adv2) vence Equipe B (Adv3) ---")
    new_a1, new_b1 = update_ratings(ENV, team_a, team_b, MatchResult.WIN_A)

    print(f"Novo Rating Adv1: mu={new_a1[0].mu:.2f}, sigma={new_a1[0].sigma:.2f} (Mudança mu: {new_a1[0].mu - adv1_rating.mu:+.2f})")
    print(f"Novo Rating Adv2: mu={new_a1[1].mu:.2f}, sigma={new_a1[1].sigma:.2f} (Mudança mu: {new_a1[1].mu - adv2_rating.mu:+.2f})")
    print(f"Novo Rating Adv3: mu={new_b1[0].mu:.2f}, sigma={new_b1[0].sigma:.2f} (Mudança mu: {new_b1[0].mu - adv3_rating.mu:+.2f})\n")

    # Atualizar ratings para o próximo cenário
    adv1_rating, adv2_rating = new_a1
    adv3_rating = new_b1[0]

    # Cenário 2: Equipe A (Adv1) empata com Equipe B (Adv4 - experiente)
    team_a_s2 = [adv1_rating] # Adv1 joga sozinho
    team_b_s2 = [adv4_rating] # Contra o experiente Adv4
    print("--- Cenário 2: Equipe A (Adv1) empata com Equipe B (Adv4 - experiente) ---")
    new_a2, new_b2 = update_ratings(ENV, team_a_s2, team_b_s2, MatchResult.DRAW)

    print(f"Novo Rating Adv1: mu={new_a2[0].mu:.2f}, sigma={new_a2[0].sigma:.2f} (Mudança mu: {new_a2[0].mu - adv1_rating.mu:+.2f})")
    print(f"Novo Rating Adv4: mu={new_b2[0].mu:.2f}, sigma={new_b2[0].sigma:.2f} (Mudança mu: {new_b2[0].mu - adv4_rating.mu:+.2f})\n")

    # Cenário 3: Equipe A (Adv1, Adv2, Adv3) perde para Equipe B (Adv4 - experiente)
    # Adv3 mudou de lado ou é um novo Adv3 para ilustração
    adv1_rating = new_a2[0] # Adv1 com rating do cenário anterior
    # adv2_rating e adv3_rating são os do final do cenário 1

    team_a_s3 = [adv1_rating, adv2_rating, adv3_rating]
    team_b_s3 = [adv4_rating] # Adv4 com rating do cenário anterior

    print("--- Cenário 3: Equipe A (Adv1, Adv2, Adv3) perde para Equipe B (Adv4) ---")
    new_a3, new_b3 = update_ratings(ENV, team_a_s3, team_b_s3, MatchResult.WIN_B)

    print(f"Novo Rating Adv1: mu={new_a3[0].mu:.2f}, sigma={new_a3[0].sigma:.2f} (Mudança mu: {new_a3[0].mu - adv1_rating.mu:+.2f})")
    print(f"Novo Rating Adv2: mu={new_a3[1].mu:.2f}, sigma={new_a3[1].sigma:.2f} (Mudança mu: {new_a3[1].mu - adv2_rating.mu:+.2f})")
    print(f"Novo Rating Adv3: mu={new_a3[2].mu:.2f}, sigma={new_a3[2].sigma:.2f} (Mudança mu: {new_a3[2].mu - adv3_rating.mu:+.2f})")
    print(f"Novo Rating Adv4: mu={new_b3[0].mu:.2f}, sigma={new_b3[0].sigma:.2f} (Mudança mu: {new_b3[0].mu - adv4_rating.mu:+.2f})\n")

    # Teste de erro
    print("--- Cenário 4: Resultado inválido ---")
    try:
        update_ratings(ENV, [ENV.create_rating()], [ENV.create_rating()], "resultado_invalido")
    except ValueError as e:
        print(f"Erro capturado como esperado: {e}")
