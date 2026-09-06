---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-uwm65t-evidence-runtime-browser-verification"
run_id: "2026-09-06-exciting-mccarthy-uwm65t"
goal_id: "2026-09-06-exciting-mccarthy-uwm65t-goal-agents-page-examples"
kind: "runtime"
reference: "npm run build (with the same public-data fixtures agents-surface-capture.yml generates) + a scratch Playwright script (chromium at /opt/pw-browsers/chromium) driving the built dist, served under a /causaganha/ base path matching production"
summary: "All four job cards render their example question and a 'Copiar pergunta' button. Clicking the decisoes_buscar card's button copies the clipboard exactly byte-for-byte to the displayed question text ('Existe alguma decisão do STJ sobre dano moral no acervo?') and shows the accessible 'Pergunta copiada.' status. Tabbing to a button and activating it with Enter (keyboard, not pointer) produces the same accessible feedback. Full-page screenshots at 1280x900 (desktop) and 390x844 (mobile) confirm correct layout in both: no overflow, one example per card, buttons and feedback text readable at mobile width. Unrelated files (web/public/og/*.svg, web/src/lib/djen-zod.gen.ts) that drifted during this local build/typecheck were reverted with `git checkout --` before committing, since they reflect this session's fixture/toolchain artifacts, not this change."
---

# Verificação em navegador real

Build local com os mesmos fixtures do workflow `agents-surface-capture.yml`, servido sob `/causaganha/` (igual produção), dirigido por um script Playwright usando o Chromium pré-instalado. Os quatro cards mostram a pergunta e o botão funciona: clique copia o texto exato para a área de transferência e mostra "Pergunta copiada."; ativação por teclado (Tab + Enter) produz o mesmo feedback. Screenshots desktop e mobile confirmam layout correto em ambos. Arquivos que sofreram drift só por causa do build/typecheck local (`web/public/og/*.svg`, `djen-zod.gen.ts`) foram revertidos antes do commit.
