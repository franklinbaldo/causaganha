---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-488tov-evidence-runtime-chromium-verification"
run_id: "2026-09-06-exciting-mccarthy-488tov"
goal_id: "2026-09-06-exciting-mccarthy-488tov-goal-export-import-saved-consultations"
kind: "runtime"
reference: "Ad hoc Playwright script driving the real `astro dev` server at /causaganha/minhas-consultas (base path from astro.config), Chromium at /opt/pw-browsers/chromium"
summary: "1) Desktop viewport (1280x900): seeded one saved processo via localStorage, clicked 'Exportar salvos', captured the real browser download — file matches schema_version=1 and items byte-for-byte. 2) Verified 'Exportar salvos' is keyboard-focusable via Tab. 3) Fresh page/context, mobile viewport (375x812), empty storage: set the downloaded file on the hidden file input -> 'Caso runtime' appeared in the list and localStorage now holds exactly the imported item (proves round-trip into empty storage and mobile usability of the import control). 4) On the same mobile page, imported a deliberately invalid file ('{ not json') -> the exact 'não é um JSON válido' error text appeared and localStorage was verified unchanged (byte-identical to before), proving atomic failure end-to-end in a real browser, not just in jsdom. All four checks printed OK; final script output: 'ALL RUNTIME CHECKS PASSED'."
---

# Evidência runtime

Verificação real em Chromium (não apenas jsdom/vitest): exportar de um contexto desktop, importar num contexto móvel com storage vazio, e importar um arquivo inválido sem corromper o storage existente — todos confirmados com o servidor `astro dev` real.
