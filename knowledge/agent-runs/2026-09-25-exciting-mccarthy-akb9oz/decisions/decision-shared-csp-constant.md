---
type: AgentDecision
id: "2026-09-25-exciting-mccarthy-akb9oz-decision-shared-csp-constant"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
question: "Um build real revelou que advogados.astro/comparador.astro renderizam seu proprio <html> em vez de usar Layout.astro, entao a CSP adicionada so a Layout.astro nao chegava a essas 2 paginas publicas. Corrigir isso fazendo-as usar Layout.astro, ou dar a cada uma sua propria copia da tag?"
choice: "Extrair a string de politica para uma constante compartilhada (web/src/lib/csp.ts::CSP_META_CONTENT) e importa-la nas 3 paginas (Layout.astro + advogados.astro + comparador.astro), cada uma renderizando sua propria tag <meta>. Nao migrar as 2 paginas para usar Layout.astro."
rationale: "CLAUDE.md documenta explicitamente que advogados.astro/comparador.astro sao 'trivial redirect stubs' -- design deliberado de pagina minima (sem nav/footer/ClientRouter) que redireciona instantaneamente via <meta http-equiv=\"refresh\">. Migra-las para Layout.astro mudaria esse design deliberado (adicionaria markup/hidratacao desnecessarios para uma pagina cujo unico papel e redirecionar) por uma razao que nao tem nada a ver com o design da pagina -- risco desproporcional ao beneficio. Duplicar a string de politica hardcoded 3x, por outro lado, criaria risco real de drift silencioso (uma futura mudanca de host/diretiva em uma copia sem atualizar as outras). A constante compartilhada resolve ambos: nenhuma migracao de design, nenhuma duplicacao de string, e o teste (Layout.csp.test.ts) passou a verificar que as 3 paginas efetivamente importam e renderizam CSP_META_CONTENT, nao apenas que Layout.astro o faz -- o teste original (regex sobre o HTML literal de Layout.astro) teria ficado cego a exatamente este gap se nao tivesse sido descoberto por build real antes do GREEN final."
---

# Decisao: constante CSP compartilhada em vez de migrar os stubs para Layout

Descoberto durante a fase GREEN (nao durante RED): `npm run build` real
mostrou que a CSP adicionada a `Layout.astro` nao aparecia em
`dist/advogados.html`/`dist/comparador.html`, porque essas duas paginas
nunca importam `Layout.astro`. Corrigido extraindo a politica para
`web/src/lib/csp.ts` e importando-a nas 3 paginas, em vez de forcar as
paginas de redirecionamento a adotar o layout completo. `Layout.csp.test.ts`
foi reescrito para verificar as 3 paginas (nao so `Layout.astro`),
capturando a licao: leitura de codigo-fonte isolada teria deixado esse gap
invisivel -- so o build real revelou.
