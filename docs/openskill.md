# OpenSkill

O CausaGanha usa a biblioteca `openskill` para calcular ratings de advogados a partir dos resultados extraídos do PDF.

## Onde fica a implementação

- Código: `src/causaganha/scoring/openskill.py`
- Pipeline: `src/causaganha/pipeline/score.py`
- Tabelas: `analysis_results` → `lawyer_ratings`

## Conceitos

- Cada advogado tem um rating representado por `(mu, sigma)`.
- Cada decisão (quem venceu/perdeu) atualiza os ratings.
- A tabela `lawyer_ratings` guarda também contadores (`wins`, `losses`, `total_cases`) para facilitar relatórios.

