---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-5lvbii-decision-batch12-candidate-selection"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
goal_id: "2026-09-16-exciting-mccarthy-5lvbii-goal-djen-sample-batch12"
question: "Which candidates should batch 12 target: chase the last few unmined tribunals (STM, TJAC, TJAM, TJAP, TJPE, TJSP, TRF1, TJSC, TRF6 -- named as exhausted by prior rounds), or add volume to already-represented but thin tribunals?"
choice: "Re-verified live (not trusted from stale backlog prose) that STM/TJAC/TJAM/TJAP/TJPE/TJSP/TRF1/TJSC/TRF6 genuinely have zero eligible unused Sentenca/Acordao candidates left in the 2500-18000 char band after excluding annotation_gold/annotation_raw auxiliary files -- confirms the exhaustion claim rather than assuming it. Picked TJES/577054686 and TJGO/543562390: both tied for lowest non-singleton store_count (2), both carry the 'preliminar' rare-category cue, and both are genuinely new -- not duplicates of each other or of anything in the store."
rationale: "knowledge/backlog/issue-1050.md's own next_move explicitly favors volume over further tribunal diversity now that diversity mining is exhausted. Picking two lowest-tier tribunals with rare-category cues serves both #1050 (document_count growth) and #1051 (more rare-category coverage for eventual independent adjudication) at once, rather than picking generic high-frequency-category filler. TJGO's texto_limpo had 364 raw HTML entities (&nbsp;, &Aacute;, etc.) -- resolved with html.unescape() per the batch2/batch7-established fix, applied uniformly to both candidates (a no-op for TJES, which had none). Neither raw text contains embedded HTML tags, so the batch3 HTML-to-text cleaner was not needed this time; confirmed via a direct regex scan and by verifying both html.unescape()'d texts parse cleanly as ET.fromstring(f'<text>{t}</text>') before spawning any annotation subagent, per zrek2s's own next_move checklist."
---

# Decisão: candidatos do lote 12 (TJES/577054686, TJGO/543562390)

Confirmado ao vivo que os tribunais historicamente citados como
"esgotados" continuam sem candidato elegível -- a estratégia de volume
(não diversidade) do próprio `next_move` de `issue-1050.md` segue
correta. TJES e TJGO, ambos no menor patamar de `store_count` (2) e
ambos com cue `preliminar`, foram escolhidos. TJGO precisou de
`html.unescape()` (364 entidades HTML brutas); nenhum dos dois tinha
markup HTML embutido.
