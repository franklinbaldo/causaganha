# RFC: Reproducibility Refactor — Parametrize Gold-Build Scratch Scripts

## Problem Statement
O dataset gold v7 (conforme descrito no PR #777) foi gerado por meio de scripts criados rapidamente ("scratch scripts"), tais como `build_gold.py`, `adjudicate.py` e scripts de verificação de ensemble, executados como tarefas únicas (one-shots) por subagentes. Embora estes scripts atinjam o objetivo de gerar o dataset, eles não são parametrizados nem reproduzíveis.

Atualmente, qualquer necessidade de reexecutar esses pipelines com conjuntos de dados (inputs) ou parâmetros diferentes requer a edição manual direta no código-fonte. A falta de reprodutibilidade compromete a rastreabilidade do experimento, aumenta a chance de erros humanos (hardcoding inadequado), dificulta revisões por pares e torna impossível a automação da recriação de datasets em pipelines CI/CD futuros. A reprodutibilidade importa porque garante que os experimentos possam ser auditados, validados e iterados por qualquer membro da equipe, produzindo de forma consistente os mesmos resultados ao partir das mesmas premissas e inputs.

## Proposed Solution
A solução proposta consiste em refatorar os scripts "scratch" (e.g., `build_gold.py`, `adjudicate.py`, ensemble verification) de modo a remover o hardcoding e expor toda a configuração como parâmetros de entrada.

A abordagem ideal será híbrida:
1. **CLI Arguments (Argumentos de Linha de Comando):** Utilizar `argparse` ou `click` (conforme padrão adotado pelo repositório) para expor os parâmetros mais voláteis (como caminhos para arquivos de input, de output e flags de verbosidade).
2. **Config Files (Arquivos de Configuração):** Para parâmetros estáticos e com múltiplas variações por versão do modelo (por exemplo, chaves de API, limiares do ensemble e diretrizes do prompt), permitir também que o script leia de um arquivo JSON ou YAML. Argumentos CLI terão precedência sobre os parâmetros de configuração caso ambos sejam fornecidos.

Os scripts também passarão a injetar metadata de reprodutibilidade no artefato gerado (por exemplo, registrando as variáveis passadas via CLI e o hash dos dados de entrada num arquivo de log/manifest de saída).

## BDD Feature Scenarios

```gherkin
Feature: Scripts parametrizados para o pipeline do Gold Dataset
  Como pesquisador de ML/Engenheiro
  Desejo rodar os scripts de geração do dataset através de parâmetros do CLI e arquivos de configuração
  Para reproduzir, auditar e versionar experimentos com diferentes inputs sem precisar modificar o código.

  Scenario: [Happy Path] Execução bem sucedida com inputs customizados via CLI
    Given o script de build "build_gold.py" está disponível e parametrizado
    When eu executo "uv run python scripts/build_gold.py --input data/raw_v8.json --output data/gold_v8.json"
    Then o script não edita variáveis de hardcode em tempo de execução
    And um dataset é gerado no caminho "data/gold_v8.json"
    And o arquivo de resultado gerado é derivado integralmente de "data/raw_v8.json"

  Scenario: [Happy Path] Execução utilizando arquivo de configuração e CLI overriding
    Given que um arquivo de configuração "config_v8.yaml" existe possuindo o campo `threshold: 0.8` e `input: data/raw_v8.json`
    When eu executo o script "adjudicate.py --config config_v8.yaml --threshold 0.9"
    Then o script deve utilizar o arquivo "data/raw_v8.json"
    And deve aplicar um threshold de "0.9", sobressaindo a diretiva do arquivo de configuração
    And o resultado de output é validado de acordo com o threshold modificado

  Scenario: [Edge Case] Argumentos mandatórios em falta
    Given o script de build "build_gold.py" está parametrizado para exigir o caminho de input obrigatoriamente (caso não haja config)
    When eu executo o script sem fornecer argumentos de input ou arquivo de configuração
    Then o script retorna um código de erro "2" e exibe uma mensagem de uso (usage/help message) indicando a falta do argumento de input

  Scenario: [Edge Case] Arquivos passados não existem
    Given o arquivo "data/invalid_path.json" não existe
    When eu executo "uv run python scripts/build_gold.py --input data/invalid_path.json"
    Then o script encerra a execução com erro
    And uma mensagem de erro clara é logada informando que o arquivo "data/invalid_path.json" não pôde ser encontrado
```

## Implementation Plan
1. **Adicionar utilitário de configuração:** Criar um módulo ou função de carregamento (ex: `config_loader.py` em `src/causaganha/pipeline` se apropriado) para lidar com a junção dos argumentos do CLI com arquivos YAML/JSON.
2. **Refatorar `build_gold.py`:**
   - Identificar e remover "hardcoded strings/variables" no código e declará-los como argumentos de CLI (`argparse`).
   - Integrar suporte a leitura de arquivos de input dinâmicos via flags.
3. **Refatorar `adjudicate.py`:**
   - Adicionar parâmetros de entrada via CLI.
   - Refatorar a passagem de parâmetros estáticos (como thresholds de decisão, seeds, metadados) para suportar configs injetáveis em runtime.
4. **Refatorar scripts de ensemble verification:**
   - Padronizar uso do `argparse`.
   - Adicionar flag para output e registro de metadados do run (para o tracking e auditoria da reprodutibilidade).
5. **Atualizar / Criar documentação (Opcional):** Atualizar scripts de uso comum (ou criar shell scripts / instruções no README/FRONTEND.md onde pertinente) para descrever a nova interface de execução parametrizada do pipeline Gold v7/v8.
6. **Implementar logging básico nas instâncias (Opcional, mas desejável):** Logar na saída padrão os parâmetros que foram efetivamente usados na subida de execução, assegurando transparência no que foi executado.

## Out of Scope
O que não será abordado por este RFC:
- Orquestração complexa (como Airflow, Prefect, Metaflow). Não construiremos um pipeline assíncrono complexo — a meta é apenas parametrizar o existente.
- Alterações lógicas e algorítmicas no modelo: as heurísticas de gold-build, adjudicação e ensemble não serão modificadas.
- Migração de scripts da pasta `scripts/` para os módulos da livraria `src/causaganha/` se o encapsulamento do refactor não o justificar agora.
- Implementação de um banco de dados rigoroso de rastreamento de ML (MLflow). Usaremos arquivos descritivos gerados ou printados pela mesma CLI em vez de depender de uma infraestrutura externa.