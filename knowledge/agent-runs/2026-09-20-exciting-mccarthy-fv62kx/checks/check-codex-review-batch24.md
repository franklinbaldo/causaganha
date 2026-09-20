---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-fv62kx-check-codex-review-batch24"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
command: "Revisao automatizada da PR #1590 pelo bot chatgpt-codex-connector (7 comentarios inline), cada um verificado ao vivo (texto-fonte, backlog historico, comparacao com documentos irmaos) antes de aceitar ou descartar."
result: "failed"
evidence_id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-codex-fixes-batch24"
summary: "5 de 7 achados confirmados reais e corrigidos: (1) TJBA/574460088 era um near-duplicate ja rejeitado no lote 17 (SequenceMatcher.ratio=0.9801 confirmado ao vivo) -- revertido do store; (2) TJGO/543517919 faltava capitulo_merito ('Decido.') -- adicionado; (3) TJGO/543517919 faltava fundamentacao_legal para '(art. 508, CPC)' -- adicionado; (4) TJPI/22443826 faltava o par cabecalho inteiro, confirmado por comparacao com documento irmao do mesmo formato -- adicionado; (5) TJMA/42725100 faltava fundamentacao_legal para a citacao do Tema 03 IRDR na propria reasoning -- adicionado. 1 achado corrigido por consistencia mas limitrofe (TJES/577051509, EC 66/2010). 1 achado parcialmente descartado apos verificacao (TJMA/42725100: as citacoes de precedente DENTRO da nota de rodape de outro tribunal permanecem sem tag, exclusao deliberada e defensavel do subagente; so a citacao do IRDR na reasoning propria foi corrigida). 1 achado tornou-se sem objeto (TJBA/574460088 EC113/Lei9494, doc revertido)."
---

# Check: revisão automatizada Codex na PR #1590 (batch24)

O bot `chatgpt-codex-connector` revisou o commit `007cf18` da PR #1590
e deixou 7 comentários inline. Nenhum foi aceito ou descartado sem
verificação ao vivo (texto-fonte bruto, `knowledge/backlog/issue-1050.md`,
documentos irmãos já no corpus):

| # | Documento | Achado | Veredito | Ação |
|---|---|---|---|---|
| 1 | TJBA/574460088 | EC113/Lei9494 sem `fundamentacao_legal` | sem objeto | doc revertido (achado 6) |
| 2 | TJGO/543517919 | `Decido.` sem `capitulo_merito` | confirmado | tag adicionada |
| 3 | TJMA/42725100 | IRDR/precedentes sem `fundamentacao_legal` | parcial: IRDR confirmado, nota de rodapé descartada | tag do IRDR adicionada + resposta na thread |
| 4 | TJES/577051509 | EC 66/2010 sem `fundamentacao_legal` | confirmado (limítrofe) | tag adicionada |
| 5 | TJGO/543517919 | art. 508 CPC sem `fundamentacao_legal` | confirmado | tag adicionada |
| 6 | TJBA/574460088 | near-duplicate já rejeitado no lote 17 | **confirmado** | documento revertido |
| 7 | TJPI/22443826 | par `cabecalho` inteiro ausente | confirmado | tag adicionada |

O achado 6 é o mais sério: `difflib.SequenceMatcher.ratio()` entre
`doc_a4274c9897fd3907743cedaec6dd4e10.xml` (TJBA/574460085, já no
store desde o lote 17) e o texto revertido = 0.9801 — confirma
exatamente o número já documentado no backlog (0.98), que a
verificação de near-duplicate desta rodada (comparação só entre os 6
candidatos do próprio lote) não capturou por comparar apenas dentro do
lote, não contra o corpus inteiro.
