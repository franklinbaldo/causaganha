# Tutorial Rápido

Este tutorial demonstra como rodar o pipeline completo localmente.

## Pré-requisitos

1.  **Python 3.12+** instalado.
2.  **uv** instalado (gerenciador de pacotes e ambiente). Se não tiver, instale com `pip install uv` ou `curl -LsSf https://astral.sh/uv/install.sh | sh`.
3.  Chave da API **Google Gemini** configurada como variável de ambiente:
    ```bash
    export GEMINI_API_KEY="SUA_CHAVE_API_AQUI"
    ```
4.  (Opcional) Clone o repositório se ainda não o fez:
    ```bash
    git clone https://github.com/franklinbaldo/causa_ganha.git
    cd causa_ganha
    ```

## Instalação e Execução

1.  **Crie um ambiente virtual e instale as dependências:**
    ```bash
    # Dentro do diretório do projeto clonado
    uv venv # Cria o ambiente .venv
    source .venv/bin/activate # Ativa o ambiente (Linux/macOS)
    # no Windows: .venv\Scripts\activate
    uv pip install -e .[dev] # Instala o projeto e dependências de desenvolvimento
    ```

2.  **(Opcional) Configure os parâmetros do TrueSkill:**
    Os parâmetros padrão do ambiente TrueSkill (como `mu`, `sigma` iniciais, `beta`, `tau`, `draw_probability`) estão definidos em `config.toml`. Você pode ajustar esses valores conforme necessário antes de executar o pipeline.

3.  **Execute o pipeline completo para uma data específica:**
    O comando `run` executa as etapas de coleta do PDF, extração de dados e atualização dos ratings.
    ```bash
    # Certifique-se que o ambiente virtual está ativado e GEMINI_API_KEY está exportada
    python -m causaganha.core.pipeline run --date AAAA-MM-DD
    ```
    Por exemplo, para a data 24 de junho de 2025:
    ```bash
    python -m causaganha.core.pipeline run --date 2025-06-24
    ```
    Alternativamente, usando `uv run` (que também pode gerenciar variáveis de ambiente se configurado no `pyproject.toml` ou via `.env`):
    ```bash
    uv run python -m causaganha.core.pipeline run --date 2025-06-24
    ```

## Verificando os Resultados

### Pipeline Assíncrono
Após a execução do pipeline assíncrono, verifique:
```bash
# Estatísticas do progresso
uv run python src/async_diario_pipeline.py --stats-only

# Status do banco distribuído
uv run python src/ia_database_sync.py status

# Descobrir itens no Internet Archive
uv run python src/ia_discovery.py --year 2025
```

### Dados Atualizados
-   `data/causaganha.duckdb`: Banco unificado com todas as tabelas
-   `data/diario_pipeline_progress.json`: Progresso do pipeline assíncrono
-   `data/diarios/`: PDFs temporários (arquivados automaticamente no IA)
-   Dados sincronizados automaticamente com Internet Archive

### Comandos de Verificação
```bash
# Verificar cobertura no Internet Archive
uv run python src/ia_discovery.py --coverage-report --year 2025

# Estatísticas do banco
causaganha db status

# Testar sistema completo
uv run pytest -q
```

## Processamento Massivo

Para processar grandes volumes de diários:

```bash
# Processar todos os diários de 2025 (115 itens)
uv run python src/async_diario_pipeline.py --input data/diarios_2025_only.json --sync-database --upload-database

# Processar todos os 5,058 diários históricos (2004-2025)
uv run python src/async_diario_pipeline.py --input data/diarios_pipeline_ready.json --max-items 100

# Ajustar concorrência para sua máquina
uv run python src/async_diario_pipeline.py --concurrent-downloads 2 --concurrent-uploads 1
```

## Troubleshooting

### Problemas Comuns

**Erro de lock de banco:**
```bash
# Forçar remoção de lock (use com cuidado)
uv run python src/ia_database_sync.py sync --force
```

**Falha de sincronização:**
```bash
# Verificar status detalhado
uv run python src/ia_database_sync.py status

# Download manual do banco do IA
uv run python src/ia_database_sync.py download --force
```

**Performance lenta:**
```bash
# Reduzir concorrência
uv run python src/async_diario_pipeline.py --concurrent-downloads 1 --concurrent-uploads 1
```

### Configuração Avançada

Crie arquivo `.env` na raiz do projeto:
```bash
GEMINI_API_KEY=sua_chave_aqui
IA_ACCESS_KEY=sua_chave_ia
IA_SECRET_KEY=sua_chave_secreta_ia
MAX_CONCURRENT_DOWNLOADS=3
MAX_CONCURRENT_IA_UPLOADS=2
```
