---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-1fxd8b-reading-issues"
run_id: "2026-09-05-exciting-mccarthy-1fxd8b"
subject: "open_issues"
reference: "https://github.com/franklinbaldo/causaganha/issues?q=is%3Aissue+is%3Aopen (30 open issues at session start)"
finding: "Issue #1135 ('Copiar referência') is now CLOSED (completed) — the previous two rounds (9xpeua, qvwrkl) finished both its acceptance criteria (/processo via PR #1148, /publicacoes via PR #1153). Issues #1138/#1139/#1145 (sitemap priority, /processo hierarchy, MCP job routing) are also resolved: their PRs #1150/#1151/#1152 all merged in the last hour by a separate concurrent process, landing the /processo hierarchy (ação -> resultado principal -> detalhes -> metodologia) that issue #1130 was explicitly blocked on. #1130 ('mostrar matriz de evidências após o resultado principal do dossiê') records its own 'Estado: READY depois do primeiro slice de #1139 em /processo' — that dependency is now satisfied, so #1130 is the natural next web slice: a compact per-source evidence-summary strip (papel Arquivo/Estado/Teor x estado presente/ausente/indisponível/não publicado x freshness) placed between resultado principal and detalhes, reusing the existing dossier contract with no new inference in the component. Other open candidates considered: #1107 (contract(processo) MCP/Web parity) is still explicitly gated 'READY após o primeiro slice da #1105' and is multi-slice by its own design — too large for one round, same conclusion as the last two rounds. #1042 (prove update-catalog end-to-end) needs live IA-upload side effects, not reproducible autonomously. #1136 (standardize loading/empty/error states) and #1131-#1134 are open but less concretely scoped than #1130 and have no unblocked dependency freshly resolved this round. The segmenter/OPF issue cluster (#884, #886-887, #1047-1057) is a large ML research track orthogonal to this round's web continuity."
---

# Leitura de issues abertas

Confirma que #1130 é o próximo passo natural: seu único bloqueio (primeira fatia de hierarquia em /processo, #1139) foi resolvido nesta última hora por PRs #1150/#1151/#1152, já mesclados antes do início desta rodada.
