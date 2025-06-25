# Este arquivo conterá a lógica para cálculos de rating usando TrueSkill.
# Serão implementadas funções para inicializar e atualizar ratings.
import trueskill

# Configurações padrão para o TrueSkill, podem ser ajustadas.
# Baseado no TEAM_RATING_PLAN.md, mu e sigma iniciais, beta, e tau.
# Draw probability também sugerido em 0.20 para o direito.
DEFAULT_MU = 25.0
DEFAULT_SIGMA = DEFAULT_MU / 3  # Aproximadamente 8.33, como no plano
DEFAULT_BETA = DEFAULT_SIGMA / 2 # Aproximadamente 4.17, como no plano
DEFAULT_TAU = DEFAULT_SIGMA / 100 # Aproximadamente 0.083, como no plano
DEFAULT_DRAW_PROBABILITY = 0.10 # Ajustado do plano (0.20 era alto), comum em jogos.

# Inicializa o ambiente TrueSkill globalmente ou passar como argumento
# O plano sugere inicializar com draw_probability=0.20
# "draw_probability=0.20 # 20% empates no direito"
# No entanto, o exemplo no final do plano usa 0.15.
# Vou usar 0.10 como um valor mais conservador inicialmente, pode ser ajustado.
ENV = trueskill.TrueSkill(
    mu=DEFAULT_MU,
    sigma=DEFAULT_SIGMA,
    beta=DEFAULT_BETA,
    tau=DEFAULT_TAU,
    draw_probability=DEFAULT_DRAW_PROBABILITY,
    # backend=None, # Pode-se especificar 'mpmath' ou 'scipy' se precisão maior for necessária
)

def create_new_rating() -> trueskill.Rating:
    """Cria um novo objeto de rating TrueSkill com os valores padrão do ambiente."""
    return ENV.create_rating()

def update_ratings(
    team_ratings_a: list[trueskill.Rating],
    team_ratings_b: list[trueskill.Rating],
    result: str, # "win_a", "win_b", "draw"
) -> tuple[list[trueskill.Rating], list[trueskill.Rating]]:
    """
    Atualiza os ratings TrueSkill para duas equipes com base no resultado da partida.

    Args:
        team_ratings_a: Lista de objetos Rating para a equipe A.
        team_ratings_b: Lista de objetos Rating para a equipe B.
        result: String indicando o resultado ("win_a", "win_b", "draw").

    Returns:
        Uma tupla contendo duas listas:
        - Novos ratings para os membros da equipe A.
        - Novos ratings para os membros da equipe B.

    Raises:
        ValueError: Se o resultado fornecido for inválido.
    """
    if result == "win_a":
        ranks = [0, 1]  # Posição 0 para o vencedor, 1 para o perdedor
    elif result == "win_b":
        ranks = [1, 0]
    elif result == "draw":
        ranks = [0, 0]  # Mesma posição para empate
    else:
        raise ValueError(f"Resultado desconhecido: {result}. Use 'win_a', 'win_b', ou 'draw'.")

    new_team_a_ratings, new_team_b_ratings = ENV.rate([team_ratings_a, team_ratings_b], ranks=ranks)
    return new_team_a_ratings, new_team_b_ratings

if __name__ == '__main__':
    # Demonstração simples de uso
    # Advogado 1 e 2 na Equipe A
    # Advogado 3 na Equipe B

    # Criar ratings iniciais para os advogados
    adv1_rating = create_new_rating() # mu=25, sigma=8.33...
    adv2_rating = create_new_rating()
    adv3_rating = create_new_rating()
    adv4_rating = trueskill.Rating(mu=30, sigma=DEFAULT_SIGMA/2) # Um advogado mais experiente

    print(f"Rating inicial Adv1: mu={adv1_rating.mu:.2f}, sigma={adv1_rating.sigma:.2f}")
    print(f"Rating inicial Adv2: mu={adv2_rating.mu:.2f}, sigma={adv2_rating.sigma:.2f}")
    print(f"Rating inicial Adv3: mu={adv3_rating.mu:.2f}, sigma={adv3_rating.sigma:.2f}")
    print(f"Rating inicial Adv4 (Experiente): mu={adv4_rating.mu:.2f}, sigma={adv4_rating.sigma:.2f}\n")

    # Cenário 1: Equipe A (Adv1, Adv2) vence Equipe B (Adv3)
    team_a = [adv1_rating, adv2_rating]
    team_b = [adv3_rating]

    print("--- Cenário 1: Equipe A (Adv1, Adv2) vence Equipe B (Adv3) ---")
    new_a1, new_b1 = update_ratings(team_a, team_b, "win_a")

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
    new_a2, new_b2 = update_ratings(team_a_s2, team_b_s2, "draw")

    print(f"Novo Rating Adv1: mu={new_a2[0].mu:.2f}, sigma={new_a2[0].sigma:.2f} (Mudança mu: {new_a2[0].mu - adv1_rating.mu:+.2f})")
    print(f"Novo Rating Adv4: mu={new_b2[0].mu:.2f}, sigma={new_b2[0].sigma:.2f} (Mudança mu: {new_b2[0].mu - adv4_rating.mu:+.2f})\n")

    # Cenário 3: Equipe A (Adv1, Adv2, Adv3) perde para Equipe B (Adv4 - experiente)
    # Adv3 mudou de lado ou é um novo Adv3 para ilustração
    adv1_rating = new_a2[0] # Adv1 com rating do cenário anterior
    # adv2_rating e adv3_rating são os do final do cenário 1

    team_a_s3 = [adv1_rating, adv2_rating, adv3_rating]
    team_b_s3 = [adv4_rating] # Adv4 com rating do cenário anterior

    print("--- Cenário 3: Equipe A (Adv1, Adv2, Adv3) perde para Equipe B (Adv4) ---")
    new_a3, new_b3 = update_ratings(team_a_s3, team_b_s3, "win_b")

    print(f"Novo Rating Adv1: mu={new_a3[0].mu:.2f}, sigma={new_a3[0].sigma:.2f} (Mudança mu: {new_a3[0].mu - adv1_rating.mu:+.2f})")
    print(f"Novo Rating Adv2: mu={new_a3[1].mu:.2f}, sigma={new_a3[1].sigma:.2f} (Mudança mu: {new_a3[1].mu - adv2_rating.mu:+.2f})")
    print(f"Novo Rating Adv3: mu={new_a3[2].mu:.2f}, sigma={new_a3[2].sigma:.2f} (Mudança mu: {new_a3[2].mu - adv3_rating.mu:+.2f})")
    print(f"Novo Rating Adv4: mu={new_b3[0].mu:.2f}, sigma={new_b3[0].sigma:.2f} (Mudança mu: {new_b3[0].mu - adv4_rating.mu:+.2f})\n")

    # Teste de erro
    print("--- Cenário 4: Resultado inválido ---")
    try:
        update_ratings([create_new_rating()], [create_new_rating()], "resultado_invalido")
    except ValueError as e:
        print(f"Erro capturado como esperado: {e}")
