# CausaGanha Documentation

Bem-vindo à documentação oficial do CausaGanha - plataforma distribuída de análise judicial.

## User Guides
- [Tutorial Rápido](quickstart.md) - Pipeline assíncrono e sincronização distribuída
- [FAQ e Limitações](faq.md) - Perguntas frequentes e limitações conhecidas

## Architecture & Implementation
- [Database Archive Implementation](database-archive-implementation.md) - Sistema de snapshots públicos no Internet Archive (✅ COMPLETO)
- [Internet Archive Discovery Guide](ia_discovery_guide.md) - Como descobrir e listar diários arquivados
- [OpenSkill Implementation](openskill.md) - Sistema de ranking OpenSkill (substituí TrueSkill)
- [Business Rules](Business_rules.md) - Regras de negócio do sistema

## Historical & Planning Documents
- [Team Rating Plan](TEAM_RATING_PLAN.md) - Planejamento histórico da transição para times (TrueSkill)
- [Architectural Review](architectural_review.md) - Revisão arquitetural do sistema
- [PDF Archival Strategy](pdf-archival-strategy.md) - Estratégia de arquivamento (planejamento)
- [Enhanced Scraping](better-scrap.md) - Melhorias na coleta de PDFs (planejamento)
- [Review 2025-06-25](review-2025-06-25.md) - Crítica e plano de ação

## Current System Status

✅ **Sistema Distribuído Operacional** (2025-06-26)
- Pipeline assíncrono para 5,058 diários históricos (2004-2025)
- Banco DuckDB compartilhado via Internet Archive com sistema de locks
- 4 workflows GitHub Actions especializados
- Arquitetura simplificada de 2 camadas (DuckDB local + Internet Archive)
- Sistema de descoberta e cobertura inteligente
- Processamento concorrente configurável

## Quick Start

```bash
# Setup inicial
git clone https://github.com/franklinbaldo/causa_ganha.git
cd causa_ganha
uv venv && source .venv/bin/activate
uv sync --dev && uv pip install -e .

# Pipeline assíncrono (recomendado)
uv run python src/async_diario_pipeline.py --max-items 5 --verbose --sync-database

# Verificar status
uv run python src/ia_database_sync.py status
uv run python src/ia_discovery.py --year 2025
```
