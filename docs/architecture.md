# Arquitetura (v2)

## Visão geral

Camadas:
- **API**: `src/causaganha/api/` (PJe client)
- **Pipeline**: `src/causaganha/pipeline/` (orquestração)
- **Storage**: `src/causaganha/storage/` (DuckDB via Ibis)
- **Analysis**: `src/causaganha/analysis/` (extração estruturada do PDF)
- **Scoring**: `src/causaganha/scoring/` (OpenSkill)
- **Services**: `src/causaganha/services/` (download de PDF, archive)

## Fluxo de dados

1) `collect`: PJe → `intimations`
2) `archive`: baixa PDF → IA (se configurado) ou local (fallback) → marca `ia_url`
3) `analyze`: baixa PDF → LLM → `analysis_results` → marca intimação como analisada
4) `score`: `analysis_results` → `lawyer_ratings` (OpenSkill)

## Schema (alto nível)

- `intimations`: metadados + link + tracking (`analyzed`, `ia_url`, etc.)
- `analysis_results`: extração do LLM (outcome, parties, oabs, etc.)
- `lawyer_ratings`: rating atual + contadores (wins/losses/total)

