# CausaGanha V2 🚀

> 🤖 **Para Assistentes de IA**: Consulte **`AGENTS.md`** para instruções de desenvolvimento.

![Alpha](https://img.shields.io/badge/status-alpha-orange?style=for-the-badge)
![Coverage](https://img.shields.io/badge/coverage-80%25-green?style=for-the-badge)

**CausaGanha** é uma plataforma distribuída de análise judicial que traz transparência ao sistema jurídico brasileiro.

*   **Objetivo:** Avaliar automaticamente o desempenho de advogados com base em resultados reais de processos.
*   **Arquitetura V2:**
    1.  **Coleta:** Busca metadados estruturados da **API de Comunicações do PJe** (substituindo web scraping V1).
    2.  **Armazenamento:** Usa **Ibis** e **DuckDB** para consultas analíticas de alta performance.
    3.  **Análise:** Usa **Pydantic AI** (Google Gemini) para extrair resultados de vitórias/derrotas de decisões em PDF.
    4.  **Pontuação:** Aplica o algoritmo **OpenSkill** para gerar rankings.
    5.  **Distribuição:** Sincroniza o banco de dados DuckDB via **Internet Archive** para acesso descentralizado.

---

## 🛠️ Instalação e Uso

### Pré-requisitos
*   Python 3.10+
*   [uv](https://astral.sh/uv/) (Gerenciador de dependências)

### Configuração Rápida

```bash
# 1. Clonar o repositório
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha

# 2. Instalar dependências
uv sync --dev

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com sua GOOGLE_API_KEY (obrigatório para análise)
```

### Comandos Principais (CLI)

O CausaGanha V2 utiliza uma CLI unificada:

```bash
# Inicializar o banco de dados
uv run causaganha db init

# Coletar intimações (TJRO, TJSP, etc.)
uv run causaganha collect --start-date 2024-01-01 --courts TJRO

# Analisar decisões (Requer GOOGLE_API_KEY)
uv run causaganha analyze --limit 10

# Calcular pontuações (OpenSkill)
uv run causaganha score

# Executar pipeline completo
uv run causaganha pipeline --courts TJRO --analyze-limit 50
```

---

## 🏗️ Desenvolvimento

Este projeto segue rigorosamente o **Test-Driven Development (TDD)**.

### Executar Testes
```bash
# Testes unitários e de integração
uv run pytest

# Teste End-to-End (Simula fluxo completo)
uv run pytest tests/e2e/test_full_lifecycle.py
```

### Qualidade de Código
```bash
# Linting e Formatação (Ruff)
uv run ruff check .

# Verificação de Tipos (MyPy Strict)
uv run mypy src/causaganha
```

---

## 📚 Documentação

A documentação completa está disponível em `docs/` e pode ser visualizada com MkDocs:

```bash
uv run mkdocs serve
```

### Estrutura do Projeto V2
*   `src/causaganha/api/`: Cliente da API PJe.
*   `src/causaganha/storage/`: Camada de dados (Ibis/DuckDB).
*   `src/causaganha/analysis/`: Agentes de IA (Pydantic AI).
*   `src/causaganha/scoring/`: Motor de pontuação (OpenSkill).
*   `src/causaganha/pipeline/`: Orquestração de fluxos.

---

## ⚖️ Licença
MIT License.
