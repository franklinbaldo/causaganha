---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-mg2tp1-decision-patch-nbsp-instead-of-redo"
run_id: "2026-09-16-exciting-mccarthy-mg2tp1"
goal_id: "2026-09-16-exciting-mccarthy-mg2tp1-goal-djen-sample-batch4"
question: "TJSC candidate 587254906's tagged output failed the ingestion script's verbatim-fidelity check with reconstructed_len==source_len (3977==3977). RFC 0012 Sec 9 treats a verbatim-fidelity mismatch as a risk signal needing independent review before retry, not an auto-reject. Given the diff turned out to be a single non-breaking-space-to-regular-space substitution in plain text between tags, should this round patch the one substring directly, or spawn a fresh subagent to redo the whole document?"
choice: "Patch the single substring directly in the subagent's tagged output file, after locating the exact diff position with a programmatic char-by-char comparison (not eyeballing) and confirming it falls in plain text, not inside or adjacent to any XML tag boundary."
rationale: "A length-preserving single-character substitution is exactly the kind of narrow, mechanically verifiable defect that RFC 0012 Sec 9's 'independent review' allows a reviewer to correct in place rather than discard -- the alternative (spawning a new subagent to redo an otherwise-correct 18-24-tag annotation because of one non-breaking space) would waste a full annotation cycle over a defect that has nothing to do with annotation quality. The fix was verified safe before applying: the diff position was checked against the tagged file's actual content and confirmed to sit in unwrapped text, not overlapping a tag, and the post-patch reconstructed text was re-diffed against source to confirm an exact match (not just re-checked for length) before re-running ingestion."
---

# Decisao: corrigir o unico caractere divergente em vez de refazer a anotacao

O candidato TJSC 587254906 falhou no check de fidelidade verbatim com
comprimentos iguais (3977==3977), mascarando uma substituicao de mesmo
tamanho. Um diff programatico caractere-a-caractere achou exatamente um
espaco nao separavel (U+00A0) trocado por espaco comum, em texto simples
sem tags por perto. Corrigido reescrevendo esse unico trecho no arquivo
do subagente, em vez de gastar um ciclo completo de subagente para
refazer uma anotacao de 18-24 tags por causa de um unico caractere.
Verificado com re-diff completo (nao so comprimento) antes de reingerir.
