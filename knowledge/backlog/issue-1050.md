---
type: BacklogItem
issue_number: 1050
title: "segmenter: repair and scale the real training corpus with agent annotation"
category: "ml_data_work"
blocking_reason: "Not actually blocked on GPU/human annotation: sibling issue #1051 proved (10+ merged PRs, 2026-09-14..16) that an isolated LLM subagent can stand in for the 'human annotator' this issue's own wording assumed, producing genuinely independent annotations and adjudicated ReviewRecords through scripts/annotate_second_independent.py + scripts/adjudicate_segmenter_review.py. This entry is kept (not deleted) because no round has yet done #1050's actual work (mining/ingesting new candidate documents to grow the corpus past 61) -- it records that the reason to skip it is gone, not that it is done."
unblock_condition: "Already unblocked. A future round should use the same agent-annotation mechanism #1051 proved to ingest new candidate documents (RFC 0012 Sec 9/#1050's own 'mine real candidate documents' work item), growing total document_count toward the ~200 the RFC's own 70/15/15 split ratios imply (150 train + 30 val + 30 test), not just adjudicate within the existing 61-document pool -- see docs/planning/evidence/segmenter-per-split-floor-ceiling-2026-09-16.json: even 100% adjudication of the current 61 documents caps val/test at 9 each, far below RFC 0012 Sec 5 item 4's >=30/>=30 floor."
last_verified_run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
last_verified_at: "2026-09-16T01:00:00Z"
status: "unblocked"
---

# Issue #1050: segmenter: repair and scale the real training corpus with agent annotation

Corrigido nesta rodada: **não está bloqueada** por falta de GPU ou
anotador humano. A issue-irmã #1051 já provou, em 10+ PRs mescladas, que
um subagente LLM isolado substitui o "anotador humano" que a redação
original desta issue presumia necessário. O que falta não é
desbloqueio — é que nenhuma rodada ainda fez o trabalho real desta issue
(minerar/ingerir novos documentos candidatos para crescer o corpus além
dos 61 atuais).

**Por que isso importa agora:** `docs/planning/evidence/segmenter-per-split-floor-ceiling-2026-09-16.json`
mostra que, mesmo com 100% de adjudicação do corpus atual de 61
documentos, `assign_splits` tem um teto matemático de val=9/test=9 —
bem abaixo do piso de RFC 0012 §5 item 4 (>=30 cada). Continuar
trabalhando #1051 isoladamente (adjudicar dentro do pool fixo) não pode
cruzar esse piso; #1050 (crescer o corpus total) é o caminho real.
