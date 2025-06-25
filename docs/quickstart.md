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
Após a execução, você encontrará os seguintes arquivos atualizados (ou criados) no diretório `data/` (ou `causaganha/data/` dependendo da estrutura final do projeto):
-   `data/diarios/dj_AAAAMMDD.pdf`: O PDF baixado.
-   `data/json/dj_AAAAMMDD_extraction.json`: O JSON extraído do PDF.
-   `data/ratings.csv`: Contém os ratings TrueSkill atualizados dos advogados.
-   `data/partidas.csv`: Histórico das partidas processadas.
-   O arquivo JSON processado também será movido para `data/json_processed/`.
```
