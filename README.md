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

📖 **Documentação Completa**: Consulte `/docs` para a documentação atualizada do projeto.

---

**CausaGanha** é uma **plataforma de análise judicial distribuída** que combina inteligência artificial, processamento assíncrono e algoritmos de avaliação de habilidades para criar um sistema automatizado de avaliação de desempenho jurídico. Utilizando o sistema **OpenSkill**, a plataforma analisa decisões judiciais para gerar rankings dinâmicos e transparentes de advogados.

## Características Principais

- **🤖 Análise por IA**: Extração automatizada via Google Gemini (via Pydantic AI)
- **📊 Sistema OpenSkill**: Avaliação dinâmica de performance jurídica
- **🌐 Distribuído**: DuckDB compartilhado via Internet Archive
- **⚡ Assíncrono**: Processamento concorrente otimizado (asyncio + Ibis)
- **🔄 Automatizado**: Workflows GitHub Actions para operação autônoma

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

### Análise com Classificador de Vencedor (ML)

É possível ativar um modelo de Machine Learning para classificar a parte vencedora de uma decisão. Use a flag `--winner-classifier` nos comandos `analyze` e `pipeline`.

- `--winner-classifier=infer`: Roda o modelo em modo de inferência, apenas para predição.
- `--winner-classifier=teach`: Roda o modelo em modo de treinamento, onde o LLM atua como "professor" para novas decisões, melhorando o modelo continuamente.

**Exemplo:**
```bash
# Rodar a análise com o classificador em modo de inferência
uv run causaganha analyze --limit 20 --winner-classifier=infer

# Rodar o pipeline completo com o classificador em modo de treinamento
uv run causaganha pipeline --start-date 2024-12-01 --winner-classifier=teach
```

```

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
