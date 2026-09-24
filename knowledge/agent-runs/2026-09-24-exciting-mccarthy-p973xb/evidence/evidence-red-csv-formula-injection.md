---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-p973xb-evidence-red-csv-formula-injection"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
kind: "test_red"
reference: "web/src/components/PublicationSearch.export.test.ts::PublicationSearch — CSV formula injection neutralization (#1612) > neutralizes cells starting with =, +, - or @, including with leading whitespace"
summary: "Novo teste, escrito antes de qualquer mudanca em csvField()/exportCurrentPageCsv(), exporta 6 publicacoes cujo campo texto comeca com =1+1/+SUM(A1:A9)/-1+2/@cmd|calc!A1/ =1+1/\\t=1+1 e afirma que a celula exportada nao comeca mais com o prefixo perigoso original. Rodado antes da correcao: FAILED -- `field.trimStart().startsWith(original.trimStart())` retorna true (a celula exportada e identica ao texto perigoso original, sem nenhuma neutralizacao), confirmando que csvField() so escapa aspas/virgulas/quebras de linha (estrutura CSV) e nao a semantica de formula de planilha. Os outros 3 testes do describe block (incluindo o de texto benigno) passaram mesmo sem a correcao, como esperado -- so a neutralizacao esta faltando."
---

# Evidencia: teste RED antes da correcao de #1612

```
$ npm run test -- src/components/PublicationSearch.export.test.ts
 ❯ src/components/PublicationSearch.export.test.ts (4 tests | 1 failed)
     × neutralizes cells starting with =, +, - or @, including with leading whitespace

AssertionError: expected true to be false // Object.is equality
- Expected: false
+ Received: true
 ❯ src/components/PublicationSearch.export.test.ts:208:66
      expect(field.trimStart().startsWith(original.trimStart())).toBe(false);
```

Confirma que o defeito descrito em TM-09/#1612 e real e reproduzivel
contra o codigo atual, antes de qualquer mudanca de producao.
