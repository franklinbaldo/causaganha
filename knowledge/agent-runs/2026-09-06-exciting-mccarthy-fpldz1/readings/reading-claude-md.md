---
type: AgentReading
id: "2026-09-06-exciting-mccarthy-fpldz1-reading-claude-md"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
subject: "claude_md"
reference: "/home/user/causaganha/CLAUDE.md as checked out at commit c8e37b4 (origin/main)"
finding: "Two runtime surfaces: Python backend (src/causaganha, src/djen_backup) and web frontend (web/, Astro 5 + Svelte 5). djen-backup treats sync-manifest.parquet on IA as sole source of truth; djen_raw is a transport code, never a verdict — availability requires HTTP 200 AND a download URL in the body. Frontend declares data needs via .qmd query contracts under web/src/queries/, rendered to web/public/data/ JSON by scripts/render_queries.py; new frontend datasets add a .qmd + Zod schema/registry entry in web/src/lib/data/contracts.ts. CSS token boundary: single Panda CSS design system via the cobogo preset; web/src/index.css is a compatibility bridge consumed only by four legacy Svelte islands (ProcessoLookup.svelte, PublicationSearch.svelte, SavedConsultations.svelte, TribunalCalendar.svelte) because panda.config.ts's include never scans .svelte files — a new Svelte component should follow the same pattern (scoped <style>, no bespoke css() call) rather than import styled-system/css directly. Style rules: ruff strict, no blind except Exception, TRY300/301/401 enforced, Python 3.12+ with | unions. Before-committing gate: uv run ruff check / ruff format --check / pytest -q. No stale-documentation drift found relevant to this round's chosen work (ProcessoLookup.svelte is explicitly one of the four legacy Svelte islands, so any change there must keep using the existing --papel-*/--s-* alias pattern, not introduce css())."
---

# Leitura de CLAUDE.md

Nenhuma lacuna de documentação detectada. A restrição mais relevante para a rodada é a fronteira CSS: `ProcessoLookup.svelte` é um dos quatro componentes legados listados explicitamente, então qualquer novo botão/ação nele deve seguir o padrão de `<style>` escopado com valores literais e classes utilitárias de `index.css`, nunca `css()` do Panda.
