---
type: AgentDecision
id: "2026-09-16-exciting-mccarthy-83kr8s-decision-accept-dangling-pairs-as-overrides"
run_id: "2026-09-16-exciting-mccarthy-83kr8s"
goal_id: "2026-09-16-exciting-mccarthy-83kr8s-goal-djen-sample-batch6"
question: "6 of 8 first-pass annotations failed mechanical validation with unmatched start/end pairs (relatorio, capitulo_merito, custas, honorarios) that _detect_allowed_unmatched doesn't auto-excuse. Re-run the subagent with corrected instructions, or declare --allowed-unmatched-overrides after inspecting the raw text?"
choice: "Inspected the tail of each of the 6 flagged documents directly (grep/tail against the tagged .txt files) before declaring any override, rather than trusting the subagent's own self-report or re-running blind. Confirmed in every case the same two known shapes already documented in knowledge/backlog/issue-1050.md's risk class 1: (a) Juizado Especial Federal/Estadual sentencas with 'relatorio dispensado' (report waived by law) -- 'RELATORIO'/'Trata-se de' opens the section but the text moves straight into fundamentacao with no distinct closing sentence; (b) a short 'Sem custas'/'honorarios' clause immediately followed by unrelated text, with no separate closing phrase. Declared one override per (candidate_id, category) pair with the specific textual reason, then re-ran ingestion with --allowed-unmatched-overrides instead of spawning a second annotation cycle."
rationale: "RFC 0012 Sec 9's own principle is 'risk signal, not auto-rejected' -- a dangling pair is exactly the class of finding a reviewing agent is supposed to inspect and judge, not blindly re-annotate away. All 6 batches so far in this lineage have needed at least one such override for the same two shapes, so re-running the subagent would likely reproduce the identical (correct) absence of a closing cue rather than fix a real defect -- costing a redundant annotation cycle for no quality gain. Verifying the raw text directly (not the subagent's self-report) before declaring the override keeps the check honest: a lazy human/agent 'trusting the LLM's own confidence' is exactly the shortcut RFC 0012 Sec 9 warns against."
---

# Decisao: aceitar pares pendentes como overrides revisados

6 dos 8 candidatos falharam a validacao mecanica na primeira passada
por pares `relatorio`/`capitulo_merito`/`custas`/`honorarios` sem cue de
fechamento. Inspecionei o texto bruto de cada um (nao apenas o
auto-relato do subagente) e confirmei as duas formas ja mapeadas na
issue #1050: relatorio dispensado em Juizado Especial, e clausulas
curtas de custas/honorarios sem frase de fechamento propria. Declarei
um override por par com o motivo especifico, em vez de rodar um
segundo ciclo de anotacao que reproduziria a mesma ausencia legitima de
cue.
