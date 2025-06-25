"""Demonstração básica do uso do módulo ``trueskill_rating``."""

from causaganha.core import trueskill_rating as ts_rating

ENV = ts_rating.ENV

# Criar ratings iniciais para os advogados usando o ENV global
adv1_rating = ENV.create_rating()
adv2_rating = ENV.create_rating()
adv3_rating = ENV.create_rating()
# Advogado experiente com rating customizado
adv4_rating = ts_rating.trueskill.Rating(mu=30, sigma=ENV.sigma / 2)

print(
    f"Usando configuração TrueSkill: Mu={ENV.mu}, Sigma={ENV.sigma}, Beta={ENV.beta}, Tau={ENV.tau}, DrawProb={ENV.draw_probability}"
)
print(f"Rating inicial Adv1: mu={adv1_rating.mu:.2f}, sigma={adv1_rating.sigma:.2f}")
print(f"Rating inicial Adv2: mu={adv2_rating.mu:.2f}, sigma={adv2_rating.sigma:.2f}")
print(f"Rating inicial Adv3: mu={adv3_rating.mu:.2f}, sigma={adv3_rating.sigma:.2f}")
print(
    f"Rating inicial Adv4 (Experiente): mu={adv4_rating.mu:.2f}, sigma={adv4_rating.sigma:.2f}\n"
)

# Cenário 1: Equipe A (Adv1, Adv2) vence Equipe B (Adv3)
team_a = [adv1_rating, adv2_rating]
team_b = [adv3_rating]
print("--- Cenário 1: Equipe A (Adv1, Adv2) vence Equipe B (Adv3) ---")
new_a1, new_b1 = ts_rating.update_ratings(ENV, team_a, team_b, "win_a")
print(
    f"Novo Rating Adv1: mu={new_a1[0].mu:.2f}, sigma={new_a1[0].sigma:.2f} (Mudança mu: {new_a1[0].mu - adv1_rating.mu:+.2f})"
)
print(
    f"Novo Rating Adv2: mu={new_a1[1].mu:.2f}, sigma={new_a1[1].sigma:.2f} (Mudança mu: {new_a1[1].mu - adv2_rating.mu:+.2f})"
)
print(
    f"Novo Rating Adv3: mu={new_b1[0].mu:.2f}, sigma={new_b1[0].sigma:.2f} (Mudança mu: {new_b1[0].mu - adv3_rating.mu:+.2f})\n"
)

adv1_rating, adv2_rating = new_a1
adv3_rating = new_b1[0]

# Cenário 2: Equipe A (Adv1) empata com Equipe B (Adv4 - experiente)
team_a_s2 = [adv1_rating]
team_b_s2 = [adv4_rating]
print("--- Cenário 2: Equipe A (Adv1) empata com Equipe B (Adv4 - experiente) ---")
new_a2, new_b2 = ts_rating.update_ratings(ENV, team_a_s2, team_b_s2, "draw")
print(
    f"Novo Rating Adv1: mu={new_a2[0].mu:.2f}, sigma={new_a2[0].sigma:.2f} (Mudança mu: {new_a2[0].mu - adv1_rating.mu:+.2f})"
)
print(
    f"Novo Rating Adv4: mu={new_b2[0].mu:.2f}, sigma={new_b2[0].sigma:.2f} (Mudança mu: {new_b2[0].mu - adv4_rating.mu:+.2f})\n"
)

adv1_rating = new_a2[0]
team_a_s3 = [adv1_rating, adv2_rating, adv3_rating]
team_b_s3 = [adv4_rating]
print("--- Cenário 3: Equipe A (Adv1, Adv2, Adv3) perde para Equipe B (Adv4) ---")
new_a3, new_b3 = ts_rating.update_ratings(ENV, team_a_s3, team_b_s3, "win_b")
print(
    f"Novo Rating Adv1: mu={new_a3[0].mu:.2f}, sigma={new_a3[0].sigma:.2f} (Mudança mu: {new_a3[0].mu - adv1_rating.mu:+.2f})"
)
print(
    f"Novo Rating Adv2: mu={new_a3[1].mu:.2f}, sigma={new_a3[1].sigma:.2f} (Mudança mu: {new_a3[1].mu - adv2_rating.mu:+.2f})"
)
print(
    f"Novo Rating Adv3: mu={new_a3[2].mu:.2f}, sigma={new_a3[2].sigma:.2f} (Mudança mu: {new_a3[2].mu - adv3_rating.mu:+.2f})"
)
print(
    f"Novo Rating Adv4: mu={new_b3[0].mu:.2f}, sigma={new_b3[0].sigma:.2f} (Mudança mu: {new_b3[0].mu - adv4_rating.mu:+.2f})\n"
)

print("--- Cenário 4: Resultado inválido ---")
try:
    ts_rating.update_ratings(ENV, [ENV.create_rating()], [ENV.create_rating()], "resultado_invalido")
except ValueError as exc:
    print(f"Erro capturado como esperado: {exc}")
