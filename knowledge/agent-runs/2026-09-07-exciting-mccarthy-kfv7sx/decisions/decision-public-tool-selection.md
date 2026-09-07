---
type: AgentDecision
id: "2026-09-07-exciting-mccarthy-kfv7sx-decision-public-tool-selection"
run_id: "2026-09-07-exciting-mccarthy-kfv7sx"
goal_id: "2026-09-07-exciting-mccarthy-kfv7sx-goal-mcp-public-profile"
question: "Besides the four canonical product tools (processo_consultar, processo_estado, publicacoes_buscar, decisoes_buscar), which of the remaining six tools (datajud_status, datajud_facetas, djen_backup_status, stj_acordaos_status, tjro_juris_status, causaganha_status) belong in the public/product profile vs the operator/local-only profile?"
choice: "Public profile = the four canonical tools + datajud_facetas + causaganha_status (6 total). Operator-only profile = datajud_status, djen_backup_status, stj_acordaos_status, tjro_juris_status (4 total, all four accept a local filesystem path argument: diretorio_dados/arquivo_manifesto/caminho_manifesto)."
rationale: "Issue #1244 explicitly asks for classification by whether a tool accepts an arbitrary local path, not by name/history: datajud_status, djen_backup_status, stj_acordaos_status and tjro_juris_status each read a caller-supplied manifest path off disk with no validation (confirmed by inspecting causaganha_mcp/http_server.py's own _PATH_ARGUMENT_TOOLS dict, which already enumerates these same four for its separate runtime guard) — none belong in a profile meant to be safe for a remote, unauthenticated caller. datajud_facetas(tribunal, por, limite) and causaganha_status() take no filesystem argument at all: datajud_facetas queries the live public DataJud API (a genuine product aggregation, exactly the kind the issue's proposal section calls out by name as a legitimate public candidate 'se seus contratos de timeout/erro forem considerados adequados ao remoto' — already true, since it has its own tighter internal timeout/retry budget and tool-level deadline distinct from the CLI's), and causaganha_status() only ever reads already-published/remote authorities (djen_published, tjro_juris_archive, stj_acordaos_archive, datajud_state), never a local path — both are remote-safe by construction, not just by absence of an obviously dangerous parameter."
---

# Decisão: quais tools entram no perfil público

Perfil público = 4 tools canônicas + `datajud_facetas` + `causaganha_status` (6). Perfil só-operador = as 4 tools que aceitam caminho local (`datajud_status`, `djen_backup_status`, `stj_acordaos_status`, `tjro_juris_status`). Classificação por parâmetro de filesystem, não por nome/histórico — exatamente como #1244 pede.
