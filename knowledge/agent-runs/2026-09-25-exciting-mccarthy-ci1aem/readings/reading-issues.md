---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-ci1aem-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-ci1aem"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, 27 abertas)"
finding: "Backlog de seguranca de docs/SECURITY_THREAT_MODEL.md: #1608/#1611/#1612/#1615/#1609(fatia Go) ja fechadas por rodadas anteriores; #1610 (metade Python+TS de URL de artefato) fechada; #1616 (core MCP untrusted-evidence marker) fechado por PR #1627 ja mesclada, mas issue permanece aberta pois seu criterio de conclusao ainda cobre processo_consultar (fora do escopo ja feito). #1613 (CSP) tem PR aberta agora mesma (#1628, sessao concorrente akb9oz), CI ainda rodando no momento desta leitura. Restam sem PR em voo: #1609 (relay Python ja fechado por #1625; so falta relay Cloudflare, documentado como dead infra, e itens de politica de deploy -- rotacao de token/quotas -- fora do controle desta sessao), #1614 (supply chain: digest de imagem/SBOM/usuario nao-root, decisoes de infraestrutura de build/deploy, historicamente fora de escopo para esta sessao), #950/TM-06 (rate limit do MCP publico) -- gap concreto e apontado explicitamente na propria matriz do threat model: 'http_server.py ja define timeout e concorrencia global; nao ha rate limit por origem/token no servidor publico'. #950 em si e um issue de produto maior (publicar endpoint remoto), mas a fatia TM-06 (rate limit por chamador) e self-contained em src/causaganha_mcp/http_server.py, sem credenciais externas, sem decisao de deploy -- so codigo + teste, seguindo o mesmo padrao de fatiamento ja usado em #1609 (Go) e #1616 (core). Demais issues abertas (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985 -- Parquet/CNJ) permanecem bloqueadas por credenciais IA ausentes neste tipo de sessao (fato ja estabelecido por 10+ rodadas anteriores); segmenter (#1050/#1051/#1057/#1056/#1055/#1054/#1047/#1053/#884/#887/#886) tem PR aberta (#1605, branch alheia); #951/#1093 sao produto de longo prazo sem gate imediato. Selecionada como trabalho principal: TM-06 (fatia de #950) via rate limiting por cliente em http_server.py."
---

# Leitura: issues abertas

27 issues abertas revisadas via `list_issues`. O backlog de seguranca
operacional (`docs/SECURITY_THREAT_MODEL.md`) segue sendo o mais tratavel
por TDD em uma rodada unica. Com TM-01/02(parcial)/03/04(parcial)/05/07/09
ja fechados ou com PR em voo por rodadas anteriores/concorrentes, o
proximo item mais tratavel sem infra de deploy e TM-06 (`#950`): rate
limit por chamador no MCP publico, ainda ausente em
`src/causaganha_mcp/http_server.py` segundo a propria matriz do threat
model -- selecionado como trabalho principal.
