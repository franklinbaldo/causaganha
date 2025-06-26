# Plano OpenSkill

**Status**: Proposta
**Prioridade**: P2 (Experimento)
**Objetivo**: Avaliar a biblioteca [OpenSkill](https://github.com/open-skill/openskill.py) como alternativa ao uso direto do `trueskill`. A ideia é habilitar ajustes mais flexíveis de ranking e lidar melhor com decisões parciais.

## Motivação
- TrueSkill é poderoso, mas suas patentes e a implementação de fator‑grafo podem ser impeditivas.
- As alternativas mais sólidas hoje são:
  - **OpenSkill**: versão Weng‑Lin/Plackett‑Luce livre de patentes, cerca de 3× mais rápida e com a mesma API de μ±σ.
  - **Glicko‑2**: apenas algumas dezenas de linhas, decay embutido, ótimo para partidas 1‑v‑1.
  - **Bradley‑Terry / Plackett‑Luce** bayesiano: flexível para cenários n‑way, mas exige infraestrutura de inferência.
- PageRank clones, Colley/Massey ou Elo cru costumam ser simples demais ou específicos de um jogo.
- Começamos avaliando o OpenSkill por ser o substituto mais próximo ao TrueSkill sem o ônus das patentes.

## Passos de Implementação
1. **Adicionar dependência**
   ```bash
   uv pip install openskill
   ```
2. **Criar módulo `openskill_rating.py`**
   - Funções para inicializar o ambiente OpenSkill.
   - Wrapper para atualizar partidas (`rate`), aceitando resultados `{win_a, win_b, partial_a, partial_b, draw}`.
3. **Ajustar pipeline**
   - Carregar parametro `rating_engine` em `config.toml` (`trueskill` ou `openskill`).
   - Em `pipeline.py`, usar o módulo correspondente ao atualizar ratings.
4. **Migração de dados**
   - Converter `ratings.csv` atual para o formato OpenSkill (mesmos campos `mu` e `sigma`).
   - Manter histórico de partidas para validação.
5. **Testes**
   - Replicar casos de `tests/test_trueskill_rating.py` para `tests/test_openskill_rating.py`.
   - Garantir que resultados idênticos (vitória/derrota simples) coincidam com TrueSkill.

## Exemplo Rápido
```python
from openskill import Rating, rate

team_a = [Rating(), Rating(mu=30)]
team_b = [Rating()]

# Vitória parcial da equipe A
new_a, new_b = rate([team_a, team_b], [0, 1], τ=0.7)
```

## Critérios de Sucesso
- Configuração do mecanismo via `config.toml`.
- Pipeline executa tanto com TrueSkill quanto com OpenSkill.
- Cobertura de testes para ambos cenários.

## Surgical Swap Recipe

Below is a concise step-by-step recipe for swapping out TrueSkill in favor of
the fully open-source **OpenSkill**. These instructions have worked for other
teams and can be executed in less than an hour.

1. **One-line dependency change**

   ```bash
   pip uninstall trueskill       # optional
   pip install openskill         # latest stable on PyPI
   ```
   OpenSkill is LGPL-3.0 and has no native extensions to compile.

2. **Update imports and initialisation**

   ```python
   # TrueSkill idiom
   import trueskill as ts
   env = ts.TrueSkill(mu=25, sigma=25/3, beta=25/6, tau=0.083)

   # OpenSkill drop-in
   from openskill.models import PlackettLuce as Skill
   model = Skill(mu=25, sigma=25/3, beta=25/6, tau=0.083)
   ```

   `PlackettLuce` is the default OpenSkill model, but you can swap to
   `BradleyTerryFull`, `BradleyTerryPart`, etc. later.

3. **Ratings object**

   ```python
   # TrueSkill
   alice = env.Rating()                # mu=25, sigma≈8.33

   # OpenSkill
   alice = model.rating(name="alice")  # same defaults
   ```

   Both expose `.mu` and `.sigma`; OpenSkill also provides
   `alice.ordinal()` (μ − 3σ).

4. **Match updates**

   ```python
   # 1‑vs‑1
   alice, bob = env.rate_1vs1(alice, bob)

   [ [alice], [bob] ] = model.rate([[alice], [bob]])

   # Arbitrary teams / ranks
   teams = [[alice, carol], [bob, dave]]
   ranks = [1, 2]  # 1 = winner, 2 = loser
   [teamA, teamB] = model.rate(teams, ranks=ranks)
   ```

   The return shape matches TrueSkill: list-of-teams with updated Rating objects.

5. **Match quality & predictions**

   | Want | TrueSkill | OpenSkill |
   |------|-----------|----------|
   | Draw / fairness metric | `env.quality(teams)` | `model.predict_draw(teams)` |
   | Win probabilities | n/a | `model.predict_win(teams)` |

6. **Persisting ratings**

   Serialising `(mu, sigma)` still works. Use
   `model.create_rating([mu, sigma], name)` when reloading.

7. **Optional shim for minimal diff**

   If you want to postpone a full refactor, create a tiny adapter
   `rating_shim.py`:

   ```python
   from openskill.models import PlackettLuce as _Skill
   _model = _Skill()

   Rating      = _model.rating
   create      = _model.create_rating
   quality     = _model.predict_draw
   rate        = _model.rate
   rate_1vs1   = lambda a, b, **kw: [l[0] for l in _model.rate([[a], [b]], **kw)]
   ```

   Then simply replace `import trueskill as ts` with `import rating_shim as ts`.

8. **What won’t be identical**

   - Parameter defaults differ slightly; run back-tests.
   - `predict_draw` may produce lower probabilities for multi-team matches.
   - Time decay is explicit via the `decay` argument on `rate`.

