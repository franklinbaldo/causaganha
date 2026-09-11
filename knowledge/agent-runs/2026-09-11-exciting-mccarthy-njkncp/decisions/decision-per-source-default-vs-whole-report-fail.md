---
type: AgentDecision
id: "2026-09-11-exciting-mccarthy-njkncp-decision-per-source-default-vs-whole-report-fail"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
question: "When indice_processual.report.json parses as valid JSON but one source entry is missing status/rows (or isn't a dict), should _carregar_cobertura drop just that source's FonteCobertura entry (or default its fields), or should the whole function return None (the same 'relatório indisponível' path used for a missing file / invalid JSON syntax)?"
choice: "Default the missing/wrong-typed field to a safe value (status='unknown', registros=0) per source and keep the entry, mirroring web/src/lib/processoCnj.ts::fetchCobertura exactly (info?.status ?? 'unknown', Number(info?.rows ?? 0)) -- not treat the whole report as unavailable."
rationale: "The report as a whole did load and parse; only one field of one source is wrong-shaped. Falling back to the report-unavailable path would throw away the generated_at timestamp and every other source's real coverage data over a single bad field -- strictly worse than the Web twin, which keeps the report and only defaults the missing piece. Matching the TS twin exactly (rather than inventing a third, Python-only degradation policy) is also what closes the Python/TS parity gap this bug is an instance of, consistent with this repo's established pattern (PR fixing #1042's redirect divergence) of treating 'the TypeScript implementation already does this correctly' as the reference behavior to converge on."
---

# Decisão: degradar por-fonte, não descartar o relatório inteiro

Escolhido replicar exatamente o comportamento do gêmeo TypeScript (`fetchCobertura`): default por campo ausente/mal-tipado, mantendo a fonte na lista e o `generated_at` do relatório, em vez de tratar o relatório inteiro como indisponível por um único campo errado.
