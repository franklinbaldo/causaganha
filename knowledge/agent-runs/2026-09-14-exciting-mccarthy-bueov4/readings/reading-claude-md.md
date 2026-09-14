---
type: AgentReading
id: "2026-09-14-exciting-mccarthy-bueov4-reading-claude-md"
run_id: "2026-09-14-exciting-mccarthy-bueov4"
subject: "claude_md"
reference: "CLAUDE.md (repo root)"
finding: "CausaGanha arquiva comunicações judiciais (DJEN) no Internet Archive e serve um dashboard público, com backend Python (src/causaganha, src/djen_backup) e frontend Astro 7 + Svelte 5 (web/). Regras centrais para esta rodada: djen_raw armazena o código HTTP bruto, nunca um veredito derivado; um 200 com corpo 'Sem comunicações' é absent, não available; 403 nunca é absent (rate limit); sync-manifest.parquet no IA é a fonte única da verdade. Fronteira de CSS: Panda via preset cobogo é o sistema único; index.css é só uma ponte de compatibilidade para 3 ilhas Svelte legadas nomeadas (ProcessoLookup, PublicationSearch, SavedConsultations) -- qualquer outro componente Svelte novo não deve introduzir custom properties bespoke fora de panda.config.ts, e deve estilizar via recipes + <style> escopado com valores literais (css() de dentro de .svelte é não confiável, pois panda.config.ts só varre .astro/.js/.jsx/.ts/.tsx). Estilo: ruff estrito, sem except Exception cego fora do bulkhead documentado em ADR-0011, TRY300/301/401 aplicados, Python 3.12+ com `from __future__ import annotations`. Antes de commitar: `uv run ruff check`, `uv run ruff format --check`, `uv run pytest -q`. Nenhuma menção a Wisk neste arquivo -- a governança do loop horário/Wisk vive só em .claude/hourly-loop.md, um arquivo separado, também lido nesta rodada (ver reading-okf)."
---

# Leitura de CLAUDE.md

Leitura integral de `CLAUDE.md` nesta rodada. Pontos mais relevantes para o trabalho de hoje: (1) contrato `djen_raw` vs `djen_status` e a regra de que 200 sem URL de download é ausente; (2) fronteira estrita Panda/CSS para componentes Svelte fora das três ilhas legadas nomeadas -- relevante porque o PR #1484 em andamento toca `DuckDBExplorer.svelte`, que não é uma das ilhas legadas e portanto não pode introduzir novas custom properties; (3) regra de `except Exception` amplo apenas com citação do ADR-0011 dentro de um bulkhead de worker pool; (4) comandos de verificação pré-commit. CLAUDE.md não menciona o runtime Wisk nem o mecanismo AgentRun -- essa governança está inteiramente em `.claude/hourly-loop.md`, tratado na leitura OKF desta rodada.
