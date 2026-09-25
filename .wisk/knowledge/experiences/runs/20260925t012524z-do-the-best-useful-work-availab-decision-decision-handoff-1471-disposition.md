---
type: "RunDecision"
id: "run-decisions/20260925t012524z-do-the-best-useful-work-availab/decision-handoff-1471-disposition"
run: "runs/20260925T012524Z-do-the-best-useful-work-available-in-this-reposi"
question: "O handoff ativo (issue #1471, publicar piloto TJRO 2026 no IA) segue bloqueado por credenciais ausentes, reconfirmado nesta rodada. Aceitar mesmo assim, reframe ou rejeitar, e o que fazer no lugar?"
decision: "reframed: mantenho o handoff ativo tal como está (não é nem aceito nem descartado -- a tarefa em si continua válida e sem alternativa viável), mas nesta rodada não avanço nele por falta de credencial; em vez disso selecionei trabalho independente e imediatamente acionável a partir das issues de segurança abertas em 2026-09-24 (#1609-#1616), especificamente #1610 (validar URLs de artefato do manifesto antes do DuckDB)."
rationale: "Repetir o diagnóstico do bloqueio de credenciais pela 12a rodada consecutiva sem produzir nenhum avanço de produto seria desperdiçar a rodada; a política anti-PR-cerimonial do repo (.claude/hourly-loop.md) já orienta não recommitar o mesmo blocker sem sinal novo. As issues de segurança recém-abertas (auditoria de threat model de 2026-09-24) são reais, testáveis por pytest puro, não dependem de credencial nenhuma, e #1610 aponta para uma injeção de SQL/URL genuína em src/causaganha/processos/service.py (arquivo_ia_url interpolado sem validação em read_parquet)."
alternatives: ["Insistir em #1471 apesar da ausência de credencial (rejeitado -- não há como progredir sem a credencial; seria a 12a reconfirmação idêntica)", "Escolher issue de segmenter (#1050 família) em vez de segurança (viável, mas #1621 já está em PR aberto cobrindo o batch mais recente e outra sessão paralela já trabalha ingest/#1611; #1610 tinha maior lacuna e nenhum PR concorrente)"]
---

# RunDecision
