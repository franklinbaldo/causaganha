---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-r0zxiq-decision-required-tribunal-kwarg"
run_id: "2026-09-25-exciting-mccarthy-r0zxiq"
goal_id: "2026-09-25-exciting-mccarthy-r0zxiq-goal-datajud-kv-metadata"
question: "Como passar a identidade do artefato (`datajud-{tribunal}`) para `datajud.archive.write_capa_parquet`/`write_movimentos_parquet` -- um novo kwarg opcional com fallback silencioso, ou um kwarg `tribunal` obrigatório que quebra a assinatura atual?"
choice: "`tribunal` vira kwarg obrigatório (`*, tribunal: str`) em `write_capa_parquet`/`write_movimentos_parquet`/`_write_parquet`, sem valor default nem shim de compatibilidade. Os três call sites existentes (`datajud/service.py::persist`, `tests/datajud/test_datajud_archive.py`, `tests/test_reconcile_processos.py`) foram atualizados para passar `tribunal` explicitamente."
rationale: "CLAUDE.md é explícito: 'Don't use feature flags or backwards-compatibility shims when you can just change the code' e 'Avoid backwards-compatibility hacks'. O precedente direto no próprio repo é `tjro_juris.service._rows_to_parquet`, que na PR #1648 (rodada anterior) tornou `item_id` um kwarg obrigatório na mesma mudança, sem fallback -- um kwarg opcional aqui permitiria silenciosamente escrever um Parquet sem o rodapé de identidade (o próprio bug que esta rodada está fechando), reintroduzindo o gap para qualquer chamador futuro que esquecesse de passar `tribunal`. `tribunal` já está disponível em todos os call sites de produção (`persist(capas, tribunal, data_dir)` já recebe `tribunal` como parâmetro)."
---

# Decisão: `tribunal` obrigatório, sem shim de compatibilidade
