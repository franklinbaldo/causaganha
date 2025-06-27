# Estratégia de Versionamento de Prompts do LLM (v3 - Baseada em Conteúdo)

## 1. Visão Geral

Este documento descreve a estratégia final para o versionamento dos prompts usados no projeto CausaGanha. A abordagem foi refinada para ser mais limpa e eficiente, focando na intenção da mudança e na imutabilidade do conteúdo.

A estratégia se baseia em três pilares:

1.  **Nomenclatura Semântica + Hash de Conteúdo**: O nome de cada arquivo de prompt combina uma descrição legível sobre seu propósito com um hash de seu conteúdo, garantindo imutabilidade.
2.  **Automação com "Circuit Breaker"**: Um script automatizado renomeia os prompts para incluir o hash, forçando o desenvolvedor a atualizar a configuração central. Se a configuração não for atualizada, os testes falham, prevenindo o uso de uma versão incorreta.
3.  **Configuração Centralizada e Rastreabilidade**: A versão ativa do prompt é definida de forma explícita e inequívoca no arquivo `config.toml` e registrada no banco de dados para cada extração.

---

## 2. Estrutura e Nomenclatura

### Diretório de Prompts

Todos os prompts são armazenados no diretório `prompts/` na raiz do projeto.

### Convenção de Nomenclatura: Descrição + Hash

O nome do arquivo de prompt terá o seguinte formato:

**`<descritivo_curto>-<hash_curto>.txt`**

Onde:
-   **`<descritivo_curto>`**: Um "slug" em kebab-case que descreve a **intenção** da mudança (ex: `versao-inicial`, `melhora-extracao-oab`, `adiciona-resumo-executivo`). Este é o componente legível por humanos.
-   **`<hash_curto>`**: Os primeiros 8 a 12 caracteres de um hash (UUIDv5 ou SHA-1) do conteúdo do arquivo. Este hash é o **garantidor da imutabilidade**.

**Exemplos de Nomes de Arquivo:**
-   `versao-inicial-a1b2c3d4.txt`
-   `melhora-extracao-oab-e5f6g7h8.txt`
-   `adiciona-resumo-executivo-9i0j1k2l.txt`

O histórico cronológico é gerenciado pelo Git, eliminando a necessidade de datas nos nomes dos arquivos.

---

## 3. Fluxo de Trabalho e Automação

Este fluxo de trabalho é projetado para ser seguro e forçar as boas práticas.

1.  **Criação/Edição Manual**: Um desenvolvedor cria ou edita um arquivo de prompt no diretório `prompts/` com um nome temporário e legível, **sem o hash**.
    -   *Exemplo*: `melhora-extracao-oab.txt`

2.  **Automação (Script/Pre-commit Hook)**: Um script automatizado (idealmente um hook de pre-commit do Git) é executado. Ele realiza as seguintes ações:
    -   Encontra todos os arquivos em `prompts/` que **não** contêm um hash no final do seu nome (antes da extensão).
    -   Para cada um desses arquivos, calcula o hash do seu conteúdo.
    -   **Renomeia o arquivo**, anexando o hash.
        -   *Exemplo*: `melhora-extracao-oab.txt` é renomeado para `melhora-extracao-oab-e5f6g7h8.txt`.

3.  **Ação Forçada pelo Desenvolvedor**: O desenvolvedor vê que seu arquivo foi renomeado automaticamente. Ele é então **obrigado** a copiar o novo nome completo do arquivo e atualizá-lo no `config.toml`.

4.  **"Circuit Breaker" nos Testes**: Se o desenvolvedor esquecer de atualizar o `config.toml`, o código que carrega o prompt falhará com um `FileNotFoundError`, pois o arquivo com o nome antigo não existe mais. Os testes automatizados irão capturar essa falha imediatamente, agindo como um "disjuntor" (circuit breaker) e prevenindo que um prompt desatualizado seja usado no pipeline.

---

## 4. Implementação Técnica

### Configuração Centralizada

O arquivo `config.toml` armazenará o nome completo e exato do arquivo de prompt a ser usado, eliminando qualquer ambiguidade.

```toml
# config.toml

[llm]
# O nome completo do arquivo de prompt a ser usado, incluindo o hash.
# Garante que a versão exata e imutável seja carregada.
extraction_prompt_file = "melhora-extracao-oab-e5f6g7h8.txt"
```

### Carregamento Dinâmico no Código

O código da aplicação carregará o prompt usando o nome de arquivo exato definido no `config.toml`.

```python
# Exemplo de implementação em src/config.py ou similar
import tomllib
from pathlib import Path

# Carregar a configuração
with open("config.toml", "rb") as f:
    config = tomllib.load(f)

LLM_CONFIG = config.get("llm", {})
PROMPT_FILENAME = LLM_CONFIG.get("extraction_prompt_file")

if not PROMPT_FILENAME:
    raise SystemExit("Erro Crítico: O arquivo de prompt não está definido em config.toml [llm.extraction_prompt_file]")

# Construir o caminho para o arquivo de prompt
PROMPT_FILE_PATH = Path("prompts") / PROMPT_FILENAME

# Carregar o conteúdo do prompt
if not PROMPT_FILE_PATH.is_file():
    raise SystemExit(f"Erro Crítico: O arquivo de prompt '{PROMPT_FILENAME}' definido em config.toml não foi encontrado.")

with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
    EXTRACTION_PROMPT = f.read()

# A variável EXTRACTION_PROMPT estará disponível para o resto da aplicação.
```

### Rastreabilidade no Banco de Dados

Para garantir a total reprodutibilidade, o nome completo do arquivo de prompt (incluindo o hash) será registrado no banco de dados.

1.  **Alteração no Schema**: A coluna `prompt_version` (do tipo `VARCHAR`) na tabela `decisoes` do DuckDB armazenará o nome do arquivo.
2.  **Registro na Inserção**: Ao salvar uma decisão extraída, o valor da variável `PROMPT_FILENAME` será incluído no registro correspondente.

---

## 5. Vantagens da Estratégia Final

-   **Foco no Propósito**: O nome do arquivo descreve *o que* o prompt faz, não *quando* foi feito. É mais limpo e semântico.
-   **Imutabilidade Absoluta**: A garantia criptográfica de que um prompt não pode ser alterado sem que seu identificador mude.
-   **Fluxo de Trabalho à Prova de Erros**: O "circuit breaker" é um mecanismo de segurança ativo que previne erros humanos de configuração.
-   **Fonte da Verdade Única**: O Git gerencia o histórico e a cronologia. O nome do arquivo gerencia a identidade e a imutabilidade do conteúdo.
