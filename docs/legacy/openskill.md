# OpenSkill Rating System Implementation

**Status**: Implementado
**Prioridade**: N/A (Concluído)
**Objetivo**: Este documento descreve a implementação do sistema de rating [OpenSkill](https://github.com/open-skill/openskill.py) no projeto CausaGanha, utilizado para ranquear advogados com base nos resultados de processos judiciais.

## Motivação para Escolha do OpenSkill

A biblioteca OpenSkill foi escolhida como o sistema de rating principal devido às seguintes vantagens:

- **Licença Permissiva**: OpenSkill (LGPL-3.0) é livre de patentes, ao contrário de algumas implementações do TrueSkill.
- **Desempenho e API**: Oferece uma API similar ao TrueSkill (μ±σ) e bom desempenho.
- **Flexibilidade**: Permite ajustes flexíveis de ranking e tem capacidade de lidar com decisões parciais (embora a lógica de identificação de decisões parciais ainda não esteja completamente implementada no pipeline).
- **Alternativa Moderna**: Considerada uma alternativa robusta a outros sistemas como Glicko-2 ou implementações bayesianas complexas para o contexto do projeto.

Originalmente, o OpenSkill foi avaliado como um substituto potencial ao TrueSkill. Após a avaliação, foi adotado como o único motor de rating do projeto.

## Componentes da Implementação

1.  **Dependência Adicionada**:
    A biblioteca `openskill` foi adicionada ao projeto via `pyproject.toml`.

    ```toml
    openskill==5.0.1
    ```

2.  **Módulo de Rating (`src/openskill_rating.py`)**:
    Um módulo dedicado foi criado para encapsular a lógica do OpenSkill. Ele inclui:
    - Funções para inicializar o modelo OpenSkill (PlackettLuce) com parâmetros configuráveis (via `config.toml` na seção `[openskill]`) ou padrões.
    - Funções para criar objetos de rating OpenSkill, tanto para novos participantes quanto a partir de valores `mu` e `sigma` existentes.
    - Uma função `rate_teams` que atualiza os ratings das equipes com base no resultado da partida (vitória, derrota, empate, ou vitória/derrota parcial).

3.  **Integração com o Pipeline (`src/pipeline.py`)**:
    - O pipeline de processamento de dados utiliza exclusivamente o módulo `openskill_rating.py` para calcular e atualizar os ratings.
    - A configuração dos parâmetros do modelo OpenSkill (`mu`, `sigma`, `beta`, `tau`) é carregada a partir da seção `[openskill]` do arquivo `config.toml`. Se a seção ou parâmetros específicos estiverem ausentes, o sistema recorre a valores padrão definidos em `openskill_rating.py`.

4.  **Formato de Dados (`ratings.csv`, `partidas.csv`)**:
    - `ratings.csv`: Armazena os ratings dos advogados, utilizando as colunas `mu` e `sigma`, que são diretamente compatíveis com o OpenSkill.
    - `partidas.csv`: Registra o histórico de partidas, incluindo os IDs dos participantes, seus ratings antes e depois, e o resultado da partida (que pode incluir "partial_a" ou "partial_b" se essa lógica for ativada no pipeline).

5.  **Testes**:
    - Testes unitários para o módulo `src/openskill_rating.py` foram criados em `tests/test_openskill_rating.py` para garantir a corretude da lógica de rating.
    - Testes de integração no pipeline (`tests/test_pipeline.py`) foram revisados e atualizados para refletir o uso exclusivo do OpenSkill.

## Configuração (`config.toml`)

A configuração dos parâmetros do OpenSkill é feita na seção `[openskill]` do arquivo `config.toml`:

```toml
[openskill]
mu = 25.0
sigma = 8.333333333333334  # Padrão: 25.0 / 3.0
beta = 4.166666666666667   # Padrão: 25.0 / 6.0
tau = 0.08333333333333333  # Padrão: (25.0 / 3.0) / 100.0
```

## Exemplo Rápido de Uso (Biblioteca OpenSkill)

```python
from openskill import Rating, rate # Exemplo direto da biblioteca

# Supondo um modelo OpenSkill já instanciado (como em openskill_rating.py)
# model = PlackettLuce(mu=25, sigma=25/3, beta=25/6, tau=0.083)

# Criar ratings para jogadores/equipes
team_a_ratings = [Rating(mu=25, sigma=8.3)] # Usando Rating direto da lib
team_b_ratings = [Rating(mu=30, sigma=7.5)]

# Calcular novos ratings após uma partida onde a equipe A venceu
# No nosso projeto, isso é encapsulado em openskill_rating.rate_teams
# new_team_a, new_team_b = model.rate([team_a_ratings, team_b_ratings], ranks=[0, 1])

# Exemplo de vitória parcial da equipe A (usando tau específico para a partida)
# new_a, new_b = model.rate([team_a_ratings, team_b_ratings], ranks=[0, 1], tau=0.7)
```

O módulo `src/openskill_rating.py` abstrai essas chamadas, facilitando o uso no pipeline.

## Considerações Futuras

- **Detecção de Resultados Parciais**: Aprimorar a lógica no `pipeline.py` para identificar resultados parciais (e.g., "parcialmente procedente") a partir dos dados extraídos e mapeá-los para `MatchResult.PARTIAL_A` ou `MatchResult.PARTIAL_B`, para que o `openskill_rating.py` possa aplicar a lógica de `tau` diferenciado para essas partidas.
- **Time Decay**: Avaliar a necessidade e implementar um mecanismo de decaimento de rating ao longo do tempo, se relevante para o projeto. OpenSkill suporta isso através do argumento `decay` na função `rate`.

```

```
