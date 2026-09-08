---
type: AgentReading
id: "2026-09-08-exciting-mccarthy-k18r9l-adr-reading-claude-md"
run_id: "2026-09-08-exciting-mccarthy-k18r9l-adr"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Re-read at the start of this round, specifically the 'No blind except Exception. Use specific types: httpx.HTTPError, httpx.RequestError, OSError, RuntimeError' rule under Style. This rule has been flagged as contradicted-in-practice by at least three prior same-day rounds (1c7t6u, b4t8pv, and this round's own predecessor k18r9l), which found 4 sites (src/djen_backup/archive.py:264, src/causaganha/analysis/llm_analyzer.py:387/499, src/causaganha/consolidate/cli.py:160) using bare `except Exception` that pass ruff's BLE001 only because their handlers call `.exception(...)` -- and each round left it unaddressed as 'needs an architectural decision, not a mechanical fix' rather than actually deciding. The live user (Franklin) explicitly directed this round, mid-session, to stop deferring: 'Nada precisa de humano. Use ADR como instrucoes e melhores praticas da industria' (nothing needs a human [decision]; use an ADR as instructions and industry best practices). The repo already has a docs/adr/ directory (one prior entry, 0010) using the standard Nygard format (Title/Date/Status/Context/Decision/Consequences), so the mechanism for recording this kind of decision already exists and just hadn't been used for this particular gap."
---

# Reading: CLAUDE.md

Releitura focada na regra "No blind except Exception", o gap arquitetural carregado por 3+ rodadas anteriores sem decisao. Instrucao explicita do usuario ao vivo nesta rodada: decidir agora via ADR, sem esperar humano.
