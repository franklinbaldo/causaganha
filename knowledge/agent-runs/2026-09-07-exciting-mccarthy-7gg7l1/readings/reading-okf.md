---
type: AgentReading
id: "2026-09-07-exciting-mccarthy-7gg7l1-reading-okf"
run_id: "2026-09-07-exciting-mccarthy-7gg7l1"
subject: "okf_knowledge"
reference: "knowledge/index.md; knowledge/okf.schema.sql; knowledge/backlog/index.md; knowledge/sources/*.md; knowledge/pipelines/*.md; tests/causaganha_mcp/test_okf_pipeline_catalog.py"
finding: "The Fonte/Pipeline slice models exactly the four continuous djen-backup-style sync engines (djen, tjro_juris, stj_acordaos, datajud) that each have a cron cadence, a dedicated GitHub Actions workflow, and an MCP *_status diagnostic tool — test_okf_pipeline_catalog.py's exact-set assertion (_EXPECTED) enforces this is closed, not open-ended. TCU (src/tcu_acordaos/) is a structurally different, one-shot annual batch publish with no cron/workflow/status tool, and decisoes_buscar's DecisionSource Literal already uses short product-facing codes ('juris','stj','tcu') that are not the same strings as the two overlapping Fonte.nome values ('tjro_juris','stj_acordaos') — there is no existing alias table between the two axes. knowledge/backlog/index.md continues to correctly describe why BacklogItem exists (to stop re-deriving the same blocked-issue reasoning every round); this round extended that same discipline to actually re-verifying each category live rather than only refreshing timestamps on trust. okf-parser check knowledge --relational-schema okf.schema.sql is conformant (641 concepts, 0 diagnostics) both before and after this round's backlog timestamp refresh."
---

# Leitura de conhecimento OKF

O modelo `Fonte`/`Pipeline` está corretamente restrito aos quatro motores de sincronização contínuos com cron/workflow/status; TCU é uma forma de publicação em lote fundamentalmente diferente e não pertence a essa relação sem um mapeamento de alias que hoje não existe entre os códigos curtos de `decisoes_buscar` e os nomes de módulo de `Fonte`. `okf-parser check` seguiu conformante durante toda a rodada.
