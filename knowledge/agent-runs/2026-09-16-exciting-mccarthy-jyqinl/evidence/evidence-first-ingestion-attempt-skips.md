---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-jyqinl-evidence-first-ingestion-attempt-skips"
run_id: "2026-09-16-exciting-mccarthy-jyqinl"
goal_id: "2026-09-16-exciting-mccarthy-jyqinl-goal-djen-sample-batch2"
kind: "runtime"
reference: "scripts/ingest_djen_sample_technique1_batch.py first run against the 8 batch2 candidates/tagged files"
summary: "First run of scripts/ingest_djen_sample_technique1_batch.py against all 8 real Technique 1 annotations (TJBA, TJGO, TJMA, TJPB, TJRJ, TJRN, TJRR, TJTO) ingested only 2 (TJPB, TJRN) and skipped 6: 3 mechanical-validation failures (unmatched capitulo_merito/custas/honorarios pairs -- TJRJ, TJMA, TJBA -- same class of dangling-pair-with-no-closing-cue documented by the previous round's batch1), and 3 genuine annotation defects never seen before: TJTO's subagent wrapped its tagged output in spurious <html><head><body><article> markup instead of the guideline's own tag vocabulary; TJGO's subagent substituted HTML named character entities (&Aacute;, &ccedil;, &atilde;, &nbsp;, &ordm;) for the literal accented UTF-8 characters in the source, producing undefined-entity XML parse errors; TJRR's subagent silently collapsed 8 occurrences of a lone-space blank line ('\\n \\n') into an empty line ('\\n\\n'), a verbatim-fidelity mismatch (5967 vs 5977 chars) invisible on a visual skim of the rendered text. Manually diffing TJRR's reconstructed text against source (difflib) confirmed all 8 diffs were exactly this one whitespace pattern, not any dropped or altered word -- ruled out attempting a manual patch after 2/8 patches applied cleanly and the rest failed on unique-substring matching (tag boundaries interfered), in favor of a supervised redo with explicit whitespace-preservation instructions, consistent with RFC 0012 Sec 9's 'risk signal, not auto-rejected' principle for anything the mechanical check alone can't safely resolve."
---

# Evidencia: primeira tentativa de ingestao do lote 2 -- 6/8 falharam

```
Ingested 2 document(s): doc_708809ec... doc_0d120692...
Skipped 6 document(s):
  285645419 (TJTO): malformed tagged XML: mismatched tag
  327514682 (TJRJ): mechanical validation failed: unmatched pair(s) ['capitulo_merito']
  42728512 (TJMA): mechanical validation failed: unmatched pair(s) ['capitulo_merito']
  543565569 (TJGO): malformed tagged XML: undefined entity
  568207813 (TJRR): verbatim-fidelity mismatch (len 5967 vs 5977)
  574460090 (TJBA): mechanical validation failed: unmatched pair(s) ['capitulo_merito', 'custas', 'honorarios']
```

Duas classes de problema distintas: 3 sao o mesmo padrao de par pendente
sem cue de fechamento ja visto no lote 1 (resolvido por override manual
revisado); 3 sao defeitos de anotacao genuinos e novos (wrapper HTML
espurio, entidades HTML no lugar de UTF-8 literal, colapso silencioso de
espacos em branco) -- resolvidos por redo supervisionado com instrucoes
explicitas, nao por patch manual (tentativa de patch manual no TJRR
corrigiu 2/8 pontos e foi abandonada por fragilidade).
