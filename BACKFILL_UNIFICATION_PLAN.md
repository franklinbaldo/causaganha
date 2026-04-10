# Plano de Unificação do Motor de Sincronização DJEN

Este documento descreve a estratégia para unificar o sistema de backup, eliminando redundâncias entre `runner.py` (coleta diária), `backfill.py` (varredura histórica) e `state.py` (cache local).

## 1. Visão Geral da Nova Arquitetura

O sistema será consolidado em um único **Motor de Sincronização** baseado em uma **Fonte Única de Verdade**: o `zip-inventory.txt` (CSV).

### Componentes Finais:
1.  **`inventory.py` (Novo):** Centraliza a classe `ZipInventory`. Gerencia o CSV que lista o que está `uploaded` ou `absent`.
2.  **`archive.py`:** Primitivas de interação com a API do Internet Archive (Upload/Download de arquivos e metadados).
3.  **`engine.py` (Consolidado):** Fusão de `runner.py` e `backfill.py`. Uma única lógica de varredura que resolve gaps de qualquer período.
4.  **`__main__.py`:** CLI simplificada que aponta para o novo motor.

## 2. Eliminação de Redundâncias

-   **Remoção do `ia-state.json` (`state.py`):** O inventário CSV já contém todas as informações necessárias. Ter um JSON paralelo é desperdício de banda e complexidade.
-   **Remoção do `runner.py`:** A coleta diária é apenas uma execução do motor com janela de tempo curta. Manter lógicas de upload/erro separadas é um risco de inconsistência.

## 3. Lógica de Sincronização Unificada

1.  **Inicialização:** Baixa o `zip-inventory.txt` e o `backfill-state.json` (progresso) do IA.
2.  **Determinação de Janela:**
    -   Se o usuário não passar `--start` e `--end`, o sistema sincroniza desde ontem até o limite de "primordial void" (60 dias vazios seguidos).
3.  **Descoberta de Gaps:**
    -   Varredura por **Tribunal x Ano** (Metadata Sync).
    -   Compara IA vs Inventário CSV vs Janela Desejada.
4.  **Processamento:**
    -   Download do DJEN -> Upload IA -> Update Inventário CSV.
5.  **Finalização:** Upload do Inventário e Progresso atualizados para o IA.

## 4. Marcos de Entrega (Milestones)

-   [ ] **M1: Centralização do Inventário:** Criar `inventory.py` e extrair a lógica do `backfill.py`. Garantir que ele seja agnóstico à finalidade da execução.
-   [ ] **M2: O Novo Motor (`engine.py`):** Implementar a lógica unificada que suporta tanto varreduras curtas (diárias) quanto longas (backfill), herdando as regras de resiliência (consecutive errors, 403 handling).
-   [ ] **M3: Refatoração da CLI:** Atualizar o `__main__.py` para usar o novo motor, mantendo a compatibilidade de comandos.
-   [ ] **M4: Limpeza (The Great Deletion):** Deletar `runner.py`, `state.py` e remover o suporte ao `ia-state.json`.
-   [ ] **M5: Validação Final:**
    -   Executar dry-run para verificar se o mapeamento de gaps continua preciso.
    -   Executar upload real de um único arquivo para confirmar o ciclo completo.

## 5. Garantia de Funcionamento (Verification)

Para garantir que a unificação não cause regressões, os seguintes testes serão realizados:
1.  **Check de Idempotência:** Rodar duas vezes o mesmo período e garantir que na segunda vez nada é baixado/subido.
2.  **Check de Inventário:** Confirmar que novos registros `uploaded` e `absent` aparecem no CSV após o processamento.
3.  **Check de Resiliência:** Simular erro 403/404 no DJEN e garantir que o tribunal é marcado como `absent` no inventário sem interromper a execução.
