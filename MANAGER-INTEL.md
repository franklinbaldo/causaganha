# MANAGER-INTEL.md

## Escopo real (o que o código realmente faz, baseado no que você leu — não suposições)
Este projeto coleta e arquiva comunicações judiciais (diários/cadernos em ZIP) da API do PJe (DJEN - Diário de Justiça Eletrônico Nacional), fazendo upload de forma contínua para o Internet Archive. Ele não apenas faz a coleta (scrape/download), mas também:
- Mantém um manifesto oficial em CSV e Parquet no Internet Archive informando se um tribunal em determinada data possui comunicações ou não.
- Processa os ZIPs diários agrupando os dados em tabelas estruturadas (Parquet) e extraindo metadados para formar um catálogo via DuckDB.
- Oferece um dashboard público web (Astro + Svelte + DuckDB-WASM) onde é possível consultar as estatísticas e as comunicações processadas.
- Possui uma ferramenta CLI flexível e com workers assíncronos que orquestram a verificação (HTTP requests para o PJe), o download dos cadernos ZIP e o upload usando regras estritas de limite de requisições e "circuit breakers".
- Contém componentes e rotinas para avaliação de decisões usando ML/RAG (pipeline causaganha).

## Fontes de dados (URLs reais, APIs reais que o código acessa)
- PJe / DJEN API Direta: `https://comunicaapi.pje.jus.br` (ex. `https://comunicaapi.pje.jus.br/api/v1/caderno/{tribunal}/{data}/D`)
- Proxy DJEN Cloud Run: `https://djen-proxy-mhgmawcn3a-rj.a.run.app` (usado primariamente em CI ou quando o acesso direto não está disponível)
- Internet Archive S3 API: Endpoints do Internet Archive para gravação e leitura (`https://archive.org/download/...`)

## Stack (linguagem, libs, formato de armazenamento de dados, package manager)
- **Linguagem Backend/Pipeline**: Python 3.12+ (gerenciado via `uv`)
- **Linguagens Frontend**: TypeScript / HTML / CSS
- **Gerenciador de pacotes Backend**: `uv` (definição no `pyproject.toml` usando padrão `project.dependencies`)
- **Gerenciador de pacotes Frontend**: `npm` (Astro/Svelte em `web/package.json`)
- **Bibliotecas Python principais**: `duckdb`, `httpx`, `structlog`, `typer`, `pydantic`, `anyio`, `rich`. O projeto não usa `boto3` para uploads no IA, forçando `httpx` para os metadados.
- **Framework Frontend**: Astro 5 + Svelte 5 (com DuckDB WASM e bibliotecas de gráficos como `@observablehq/plot`).
- **Formato de armazenamento de dados**: Arquivos `.zip` brutos no IA, `.parquet` para tabelas consolidadas, `.csv` para manifesto e DuckDB local.

## Como rodar (comando exato para ingestão, testes)
- **Setup básico**:
  ```bash
  uv sync --dev
  cp .env.example .env
  uv run pre-commit install
  ```
- **Rodar os testes Python**:
  ```bash
  uv run pytest -q
  ```
- **Rodar a ingestão/coleta (DJEN Backup)**:
  ```bash
  uv run djen-backup --workers 8
  ```
- **Construir/Testar Frontend**:
  ```bash
  cd web
  npm ci
  npm run lint
  npm test
  npm run build
  ```

## Estado atual (o que funciona, o que está quebrado)
- O pipeline de coleta diária, consolidação e deploy está operando sob forte automação via GitHub Actions. A maioria das funções nucleares funciona, conforme testes contínuos rodados em PRs.
- Não existem evidências nos arquivos do repo de bugs críticos, mas as issues demonstram melhorias focadas em DevOps/Reproducibilidade.
- A migração do projeto de queries fixas no back end (JSON cache) para `.qmd` contracts com geração dinâmica durante o build está concluída/em operação (`scripts/render_queries.py`).
- Há uma ressalva operacional de timeouts na GitHub action de collect-zips que precisou ter o threshold máximo estendido de 17min/19min para 25minutos devido ao excessivo "cleanup time" durante upload do manifesto.

## Issues abertas (top 5, com números e resumo de uma linha)
- **#794**: docs: add RFC for reproducibility refactor of gold-build scripts (Proposta de refatoração para reprodutibilidade de scripts em /gold-build)
- **#793**: chore(deps): bump the npm_and_yarn group across 1 directory with 4 updates (Atualização de dependências via Dependabot/Renovate)
- **#792**: feat(train): headless Colab GPU training via google-colab-cli (Permitir treino headless na infra do Colab com a CLI google-colab)
- **#779**: Reproducibility refactor: parametrize gold-build scratch scripts (Task concreta de parametrização dos scripts scratch /gold-build)
- **#662**: web: design-quality PNGs for og-image and apple-touch-icon (Necessidade de adicionar assets visuais de qualidade como og-images/favicons)

## PRs abertas (número, título, estado)
- **#794**: docs: add RFC for reproducibility refactor of gold-build scripts (open)
- **#793**: chore(deps): bump the npm_and_yarn group across 1 directory with 4 updates (open)
- **#792**: feat(train): headless Colab GPU training via google-colab-cli (open)

## Próximas sessões Jules recomendadas (top 3 tarefas concretas com issue numbers)
1. **Atacar Issue #779**: Implementar a refatoração baseada no RFC detalhado no PR #794 para os scripts `build_gold.py`/`adjudicate.py`, trocando hardcoded vars por CLI args (`typer` ou `argparse`).
2. **Atacar Issue #792**: Desenvolver/integrar pipeline headless com `google-colab-cli` para automatizar execuções do Jupyter Notebook (`notebooks/train_decision_segmenter.py` e ML).
3. **Atacar Issue #662**: Criar/importar os assets estáticos `og-image.png` e `apple-touch-icon.png` no layout Svelte/Astro do `web/public` e inserí-los no `<head>` dos layouts bases no frontend.
