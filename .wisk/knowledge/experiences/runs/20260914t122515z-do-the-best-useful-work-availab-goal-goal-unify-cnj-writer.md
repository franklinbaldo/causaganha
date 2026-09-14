---
goal: "Avançar a issue #1469 (parte de #1468): unificar o writer de Parquet (exporter.py + _export_table_sync legado em scripts/pipeline/consolidate.py), normalizar numero_processo para texto de 20 dígitos na escrita (preservando não-CNJ/nulo/máscara), reordenar comunicacoes/processos por (numero_processo, data, ...) e certificar via KV_METADATA no rodapé (causaganha.layout=cnj-text-sorted-v1, causaganha.cnj_normalization=valid-20-digits-v1), disparando reconsolidação via bump de CURRENT_LAYOUT_REVISION. Escopo desta rodada é só backend (Python); a leitura no site (web/src/lib/processoCnj.ts) fica para a próxima rodada, sem quebrar o fallback compatível existente."
id: "run-goals/20260914t122515z-do-the-best-useful-work-availab/goal-unify-cnj-writer"
kind: "task-advance"
rationale: "É o primeiro item de entrega concreto e testável do épico #1468 (Parquet nativo/CNJ), com trabalho de auditoria e decisão já registrados nas issues; a infraestrutura de gatilho de reconsolidação (layout_revision) já existe e só precisa ser usada. Fazer isso agora evita que a preparação local mencionada na issue #1469 fique presa fora do repositório."
run: "runs/20260914T122515Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "pytest verde para novos testes RED->GREEN de normalização de CNJ, nova ordenação e certificação KV_METADATA; _export_table_sync em scripts/pipeline/consolidate.py delega para causaganha.consolidate.exporter.export_table_sync (sem lógica duplicada de COPY); PR aberto no GitHub referenciando #1469."
type: "RunGoal"
---

# RunGoal
