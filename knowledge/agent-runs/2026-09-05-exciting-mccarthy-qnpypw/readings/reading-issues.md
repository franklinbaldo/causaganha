---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-qnpypw-reading-issues"
run_id: "2026-09-05-exciting-mccarthy-qnpypw"
subject: "open_issues"
reference: "GitHub open issues, franklinbaldo/causaganha (26 total at session start, listed via list_issues)"
finding: "A brand-new issue, #1168 ('reboot(web): reconstruir a experiência pública sobre Cobogó/Panda', opened 2026-09-05T23:17:29Z by the repo owner), asks for a from-scratch rebuild of the entire web/ surface onto Panda CSS + a new 'Cobogó' design-system preset, replacing Pico as the visual foundation while preserving data contracts/routes/SEO/a11y. This supersedes the smaller pending web-UX issues (#1131-1136, #1093): #1168's own body says it should 'absorver, não atropelar' the in-flight IA/UX work (#1136, #1138, both already merged into main by the time this round started). The rest of the backlog is materially unchanged from prior rounds' characterization: the segmenter chain under #1047 (#1050-1057) remains gated on real double-annotation or a GPU training run; #1011/#985/#951/#950/#1022 remain gated on live, hard-to-reverse Internet Archive/deploy actions needing explicit sign-off; #924 (the Ox Alpha automated-review meta-issue) has only SS3.5 (layout_revision backfill policy, needs live IA sampling) still open, everything else already closed by earlier rounds. One issue moved from 'READY, needs one more live smoke test' to fully closeable this round: #1042 ('ops(catalog): provar update-catalog ponta a ponta após #1040') had 12 prior comments, each finding the pipeline evidence already solid (run #776, 2026-09-03) but explicitly leaving open only the last step — comparing processo_consultar (MCP) against /processo (web) for the same real CNJ, without a fixture/fallback. No round had closed that last gap yet."
---

# Leitura de issues abertas

Achado central: **#1168** é um pedido de reconstrução total do frontend (Panda CSS/Cobogó), aberto minutos antes desta rodada, que suplanta as issues pequenas de web-UX ainda pendentes. Fora isso, o backlog segue como caracterizado por rodadas anteriores (segmentador gated em anotação/GPU; ops/dados gated em efeitos colaterais irreversíveis). A lacuna real e fechável nesta rodada foi a **#1042**: faltava só a última prova de paridade MCP×web para um CNJ real, pendente havia 12 comentários.
