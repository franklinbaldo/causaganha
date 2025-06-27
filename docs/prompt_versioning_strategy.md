# Estratégia de Versionamento de Prompts do LLM

## 1. Visão Geral

Este documento descreve a estratégia adotada para o versionamento dos prompts usados para interagir com o Large Language Model (LLM) no projeto CausaGanha. O objetivo é garantir a reprodutibilidade, rastreabilidade e estabilidade do pipeline de extração de dados, tratando os prompts como artefatos de software de primeira classe.

A estratégia se baseia em três pilares principais:

1.  **Arquivos de Texto Versionados**: Armazenar prompts em arquivos de texto externos, com nomes que seguem o padrão de Versionamento Semântico (SemVer).
2.  **Configuração Centralizada**: Gerenciar a versão ativa do prompt através do arquivo de configuração `config.toml`.
3.  **Rastreabilidade no Banco de Dados**: Registrar a versão do prompt usada para cada extração na tabela `decisoes` do DuckDB.

---

## 2. Estrutura e Nomenclatura

### Diretório de Prompts

Todos os prompts serão armazenados em um novo diretório na raiz do projeto:

```
prompts/
└── extraction_prompt_v1.0.0.txt
```

Isso isola os prompts do código da aplicação, facilitando seu gerenciamento.

### Convenção de Nomenclatura (Versionamento Semântico)

Os arquivos de prompt seguirão o padrão `extraction_prompt_vMAJOR.MINOR.PATCH.txt`.

-   **`MAJOR`** (ex: `v1.0.0`, `v2.0.0`): Será incrementado para **mudanças incompatíveis** na estrutura do JSON de saída. Qualquer alteração que quebre o parsing do lado do código (ex: renomear um campo obrigatório, remover um campo) exige um incremento da versão `MAJOR`.

-   **`MINOR`** (ex: `v1.1.0`, `v1.2.0`): Será incrementado para **novas funcionalidades compatíveis com versões anteriores**. Isso inclui adicionar um novo campo opcional ao JSON de saída ou enriquecer significativamente a informação de um campo existente sem quebrar o formato.

-   **`PATCH`** (ex: `v1.0.1`, `v1.1.1`): Será incrementado para **correções e melhorias que não alteram a estrutura do JSON**. Isso inclui refinar a linguagem do prompt, corrigir erros de digitação, adicionar ou melhorar exemplos para o LLM, ou otimizar as instruções para melhorar a precisão da extração.

Esta convenção comunica claramente o impacto de cada mudança, prevenindo que uma simples edição no prompt quebre o pipeline de forma inesperada.

---

## 3. Implementação Técnica

### Configuração Centralizada

A versão do prompt a ser utilizada pelo pipeline será definida no arquivo `config.toml` para permitir a fácil alteração sem a necessidade de modificar o código.

```toml
# config.toml

[llm]
# Define a versão do prompt de extração a ser usada em todo o sistema.
# O arquivo correspondente deve existir em /prompts/extraction_prompt_v<versao>.txt
extraction_prompt_version = "1.0.0"
```

### Carregamento Dinâmico no Código

O código da aplicação (especificamente `src/extractor.py` ou um módulo de configuração) será responsável por carregar dinamicamente o prompt com base na versão especificada no `config.toml`.

```python
# Exemplo de implementação
import tomllib
from pathlib import Path

# Carregar a configuração
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

LLM_CONFIG = config.get("llm", {})
PROMPT_VERSION = LLM_CONFIG.get("extraction_prompt_version", "1.0.0") # Usar um default seguro

# Construir o caminho para o arquivo de prompt
PROMPT_FILE_PATH = Path("prompts") / f"extraction_prompt_v{PROMPT_VERSION}.txt"

# Carregar o conteúdo do prompt
if not PROMPT_FILE_PATH.is_file():
    raise SystemExit(f"Erro Crítico: O arquivo de prompt v{PROMPT_VERSION} não foi encontrado em {PROMPT_FILE_PATH}")

with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
    EXTRACTION_PROMPT = f.read()

# A variável EXTRACTION_PROMPT estará disponível para o resto da aplicação.
```

### Rastreabilidade no Banco de Dados

Para garantir a total reprodutibilidade e facilitar a depuração, a versão do prompt utilizada em cada extração será registrada no banco de dados.

1.  **Alteração no Schema**: Uma nova coluna, `prompt_version` (do tipo `VARCHAR`), será adicionada à tabela `decisoes` no DuckDB.

2.  **Registro na Inserção**: Ao salvar uma decisão extraída no banco de dados, o valor da variável `PROMPT_VERSION` será incluído no registro correspondente.

Isso permitirá, no futuro, a análise de performance de diferentes versões de prompt e a identificação precisa da origem de possíveis lotes de dados mal extraídos.

---

## 4. Fluxo de Trabalho para Atualização de Prompt

1.  **Criar Novo Arquivo**: Ao modificar um prompt, o desenvolvedor deve criar um **novo arquivo** em `prompts/` com o número de versão incrementado de acordo com a regra do SemVer.
2.  **Testar Localmente**: O desenvolvedor deve atualizar a variável `extraction_prompt_version` em seu `config.toml` local para testar o novo prompt.
3.  **Atualizar Configuração**: Uma vez validado, a alteração no `config.toml` pode ser submetida (commitada) para que o novo prompt seja usado em produção no próximo ciclo do pipeline.
4.  **Não modificar arquivos existentes**: Prompts versionados nunca devem ser modificados. A criação de um novo arquivo garante um histórico imutável.
