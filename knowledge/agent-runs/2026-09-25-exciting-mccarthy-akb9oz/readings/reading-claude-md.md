---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-akb9oz-reading-claude-md"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Releitura integral no inicio da rodada. Fronteira CSS/Panda relevante ao trabalho escolhido (#1613, CSP + piso XSS): 'Nao invente propriedades customizadas fora de panda.config.ts' e a nota de que Panda so escaneia .astro/.ts/.tsx (nunca .svelte) -- logo Svelte usa estilos globais + <style> escopado, nunca css() direto. Isso e diretamente relevante: os componentes Svelte do app emitem <style> inline no HTML final (confirmado por build local), entao qualquer CSP que proiba style-src inline quebraria toda pagina com ilha Svelte -- decisao registrada em decision-style-src-unsafe-inline. Regra de estilo (ruff/TRY300/TRY301, sem except Exception generico) nao se aplica -- trabalho desta rodada e TypeScript/Astro puro, sem tocar Python. Regra 'nao adicionar tratamento de erro para cenarios que nao podem acontecer' seguida: nenhum try/catch novo, apenas testes estaticos (leitura de arquivo fonte) e uma meta tag declarativa."
---

# Leitura: CLAUDE.md

Releitura integral do guia do projeto no inicio da rodada, conforme exigido
pelo contrato `AgentRun`. O trabalho desta rodada (fechar #1613, CSP + piso
de regressao XSS) fica em `web/src/layouts/Layout.astro`,
`web/src/pages/advogados.astro`, `web/src/pages/comparador.astro` e
`web/src/lib/djen.ts` (TypeScript/Astro/Vitest) -- fora do escopo direto das
regras de estilo Python, mas a fronteira CSS/Panda documentada no arquivo
(Svelte nunca usa `css()`, sempre `<style>` escopado) foi decisiva para a
politica de `style-src` do CSP.
