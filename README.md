# CausaGanha

> 🤖 **Para Assistentes de IA**: Consulte **`CLAUDE.md`** para instruções completas de desenvolvimento, incluindo abordagem plan-first, coordenação MASTERPLAN, e guidelines específicas para agentes de código.

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![Breaking Changes](https://img.shields.io/badge/breaking_changes-expected-red?style=for-the-badge)
![No Backwards Compatibility](https://img.shields.io/badge/backwards_compatibility-none-critical?style=for-the-badge)

[![Update OpenSkill Ratings](https://img.shields.io/github/actions/workflow/status/franklinbaldo/causa_ganha/03_update.yml?label=update-openskill)](https://github.com/franklinbaldo/causa_ganha/actions/workflows/03_update.yml)

> ⚠️ **SOFTWARE ALPHA**: Este projeto está em desenvolvimento ativo com mudanças radicais frequentes. APIs, schemas de banco de dados e funcionalidades principais podem mudar sem aviso ou compatibilidade com versões anteriores. Use por sua conta e risco em ambientes de produção.

## 🚀 CausaGanha V2 (Implementado)

O **CausaGanha V2** já está implementado e em fase de testes e estabilização (Fase 4). A arquitetura foi migrada com sucesso para utilizar a API do PJe, DuckDB via Ibis e Pydantic AI.

### Principais Mudanças da v2 (Completas)

- **Coleta de Metadados**: Web scraping → API de Comunicações PJe (JSON estruturado)
- **Operações de Dados**: pandas → Ibis (10-100x mais rápido)
- **Integração LLM**: SDK direto Gemini → Pydantic AI (agnóstico de provedor)
- **Cobertura**: Apenas TJRO → 90+ tribunais com suporte PJe

### Status do Desenvolvimento v2

- ✅ **Fase 0**: Preparação do repositório e estrutura de diretórios v2
- ✅ **Fase 1**: Implementação v2 baseada em TDD (Core)
- ✅ **Fase 2**: Integração e Validação
- ✅ **Fase 3**: Expansão Multi-Tribunal e Infraestrutura Cloud
- 🔄 **Fase 4 (Atual)**: Testes E2E, Documentação e Hardening

## 📖 Documentação Completa

O projeto possui documentação abrangente em inglês na pasta `/docs`:

### Estratégia e Visão
- [`PRODUCT_VISION.md`](docs/PRODUCT_VISION.md) - Visão do produto, personas de usuários e métricas de sucesso
- [`ROADMAP.md`](docs/ROADMAP.md) - Roadmap de features priorizadas e cronograma (MVP → Monetização)
- [`MVP_SCOPE.md`](docs/MVP_SCOPE.md) - Escopo do MVP e definição de "pronto"
- [`PERSONAS.md`](docs/PERSONAS.md) - Personas detalhadas e jornadas de usuário

### Requisitos Técnicos e Legais
- [`TECHNICAL_REQUIREMENTS.md`](docs/TECHNICAL_REQUIREMENTS.md) - Alvos de escala e especificações de performance
- [`COMPLIANCE.md`](docs/COMPLIANCE.md) - Requisitos legais e regulatórios (LGPD, OAB)

### Testes BDD
- [`tests/features/README.md`](tests/features/README.md) - **459+ cenários BDD** organizados por prioridade de negócio
- 13+ arquivos .feature cobrindo todos os aspectos da plataforma
- **Parquet Analysis**: 100+ cenários adicionais documentando workflows avançados
  - [`tests/features/parquet_schema_v2/`](tests/features/parquet_schema_v2/) - Schema v2 com embeddings separados
  - [`tests/features/parquet_advanced/`](tests/features/parquet_advanced/) - 89 cenários de workflows avançados

---

**CausaGanha** é uma **plataforma de análise judicial distribuída** que combina inteligência artificial, processamento assíncrono e algoritmos de avaliação de habilidades para criar um sistema automatizado de avaliação de desempenho jurídico. Utilizando o sistema **OpenSkill**, a plataforma analisa decisões judiciais para gerar rankings dinâmicos e transparentes de advogados.

## Características Principais

- **🤖 Análise por IA**: Extração automatizada via Google Gemini (via Pydantic AI)
- **📊 Sistema OpenSkill**: Avaliação dinâmica de performance jurídica
- **🌐 Distribuído**: DuckDB compartilhado via Internet Archive
- **⚡ Assíncrono**: Processamento concorrente otimizado (asyncio + Ibis)
- **🔄 Automatizado**: Workflows GitHub Actions para operação autônoma
- **🔮 Previsão de Vencedor**: Subsistema opcional com embeddings e aprendizado online para prever resultados (Novo)

## Instalação Rápida

```bash
# Instalar uv (gerenciador de dependências)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clonar e configurar
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha
uv venv && source .venv/bin/activate
uv sync --dev && uv pip install -e .

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas chaves API (GEMINI_API_KEY é obrigatória)
```

## Uso Básico

```bash
# Inicializar banco de dados
uv run causaganha db init

# Executar pipeline completo (Coleta -> Arquivamento -> Análise -> Scoring)
uv run causaganha pipeline --courts TJRO --start-date 2024-12-01

# Comandos individuais
uv run causaganha collect --courts TJRO
uv run causaganha archive --limit 10
uv run causaganha analyze --limit 5
uv run causaganha score
```

### Análise Baseada em Parquet (Internet Archive)

O CausaGanha utiliza uma **arquitetura multi-parquet** para armazenar e analisar decisões judiciais:

```bash
# Download de parquet do Internet Archive
uv run causaganha parquet download --tribunal TJRO --date 2025-01-15

# Analisar decisões de arquivo parquet local
uv run causaganha parquet analyze --file decisions-2025-01-15-TJRO.parquet

# Analisar diretamente do Internet Archive
uv run causaganha parquet analyze-ia --tribunal TJRO --date 2025-01-15
```

**Arquitetura:**
- **Decisões**: Texto completo, análise, confiança (SEM embeddings)
- **Embeddings**: Arquivo separado para flexibilidade e regeneração
- **Advogados**: Perfis e ratings em arquivo separado
- **Partes**: Informações das partes processuais

**Benefícios:**
- ✅ Análise 3-5x mais rápida (embeddings em cache)
- ✅ Economia de $8K/ano (reutilização de embeddings)
- ✅ Queries DuckDB remotos (sem download necessário)
- ✅ Reprocessamento incremental (corrigir erros históricos)
- ✅ Armazenamento ilimitado no Internet Archive

Veja [`docs/SCHEMA_V2_FINAL_RECOMMENDATIONS.md`](docs/SCHEMA_V2_FINAL_RECOMMENDATIONS.md) para detalhes da arquitetura.

---

### Previsão de Vencedor (Winner Prediction)

O subsistema opcional de previsão de vencedor permite treinar um modelo leve (SGD) usando embeddings do texto da decisão para prever se o autor ou réu venceu.

```bash
# Apenas inferência (usa modelo existente)
uv run causaganha analyze --limit 10 --winner-classifier infer

# Treinamento com Professor (LLM) + Bootstrap automático
uv run causaganha analyze --limit 10 \
    --winner-classifier teach \
    --winner-bootstrap auto \
    --winner-bootstrap-limit 2000 \
    --jobs 8
```

Modos:
- `off`: Desabilitado (padrão).
- `infer`: Calcula embedding e prevê resultado.
- `teach`: Calcula embedding, prevê, consulta LLM ("Professor") para label real e atualiza o modelo.

Bootstrap:
- O sistema pode treinar automaticamente com decisões históricas já analisadas no banco de dados para evitar "cold start".

## Variáveis de Ambiente

```bash
GEMINI_API_KEY=sua_chave_gemini    # Obrigatório para extração
IA_ACCESS_KEY=sua_chave_ia         # Opcional (para upload no Internet Archive)
IA_SECRET_KEY=sua_chave_secreta_ia # Opcional (para upload no Internet Archive)
COURTS=["TJRO","TJAC"]             # Lista de tribunais padrão
```

## Testes

```bash
# Rodar todos os testes
uv run pytest

# Rodar teste E2E (Ciclo completo)
uv run pytest tests/e2e/test_full_lifecycle.py
```

## Licença

Este projeto é licenciado sob os termos da MIT License.
