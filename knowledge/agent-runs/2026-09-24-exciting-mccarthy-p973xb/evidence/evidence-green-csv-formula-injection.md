---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-p973xb-evidence-green-csv-formula-injection"
run_id: "2026-09-24-exciting-mccarthy-p973xb"
kind: "test_green"
reference: "web/src/components/PublicationSearch.svelte::csvField; web/src/components/PublicationSearch.export.test.ts"
summary: "Corrigido csvField() em web/src/components/PublicationSearch.svelte para prefixar com um apostrofo qualquer celula cujo primeiro caractere significativo (ignorando espacos/tabs iniciais) seja =, +, - ou @ -- a tecnica padrao de neutralizacao de CSV/formula injection, aplicada antes do quoting RFC ja existente (aspas/virgulas/quebras de linha), sem alterar a apresentacao normal na UI (so a serializacao do arquivo exportado muda) nem o escopo/paginacao/nome do arquivo. Os 4 testes do novo describe block (incluindo o antigo teste de escopo/paginacao, que continua verde) passam: os 6 prefixos perigosos do gate automatizado pedido pela issue #1612 (=1+1, +SUM(A1:A9), -1+2, @cmd|calc!A1, e as variantes com espaco/tab iniciais) ficam inertes, e 4 strings benignas com caracteres relacionados mas nao perigosos (10% de multa, (vide anexo), R$ 1.000,00, Intimacao sobre honorarios) permanecem byte-a-byte identicas."
---

# Evidencia: GREEN apos a correcao de #1612

```
$ npm run test -- src/components/PublicationSearch.export.test.ts
 Test Files  1 passed (1)
      Tests  4 passed (4)
```

`csvField`:

```ts
const DANGEROUS_CSV_PREFIX = /^[ \t]*[=+\-@]/;

function csvField(value: unknown): string {
  const raw = value == null ? '' : String(value);
  const text = DANGEROUS_CSV_PREFIX.test(raw) ? `'${raw}` : raw;
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}
```
