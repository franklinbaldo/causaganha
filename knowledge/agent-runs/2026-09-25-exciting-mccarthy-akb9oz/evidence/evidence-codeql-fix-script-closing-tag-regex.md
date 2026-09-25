---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-codeql-fix-script-closing-tag-regex"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "review"
reference: "PR #1628 review comment 4102895727 (CodeQL, github-advanced-security[bot]); check run CodeQL (108009738210, 1 high severity alert); web/scripts/injectCspHashes.mjs:28"
summary: "CodeQL sinalizou 1 alerta de severidade alta em web/scripts/injectCspHashes.mjs:28 ('Bad HTML filtering regexp: This regular expression does not match script end tags like </script >'). INLINE_SCRIPT_RE usava /<\\/script>/ para o limite de fechamento -- nao reconhece </script > (com espaco antes do >), que e uma tag de fechamento valida pelo tokenizer HTML5. Isso e uma falha real, nao cosmetica: se um build de producao algum dia emitir esse padrao (framework/minificador diferente, ou uma mudanca futura no Astro/Vite), a regex continuaria escaneando ate o PROXIMO '</script>' literal no documento, fundindo silenciosamente conteudo nao relacionado no hash computado -- o hash resultante nao bateria com o que o navegador realmente executa como o elemento script discreto, quebrando a hidratacao naquele caso (o mesmo tipo de falha, por coincidencia, que este script inteiro existe para evitar). Corrigido trocando o limite de fechamento para /<\\/script\\s*>/ (aceita zero ou mais espacos antes do '>'), TDD: 1 teste novo RED-then-GREEN (html com '</script >' com espaco, confirmando que o script anterior ficava vazio -- computeInlineScriptHashes retornava [] em vez do hash esperado -- antes da correcao)."
---

# Evidencia: CodeQL (alta severidade) corrigido -- regex de fechamento de `<script>`

```
$ npx vitest run scripts/injectCspHashes.test.ts   # ANTES da correcao
 ❯ recognizes a closing tag with whitespace before '>' ...
AssertionError: expected [] to deeply equal [ Array(1) ]
- Expected: ["3xqCEfNrbhQLAZy5uSLzJ9hNthXm1py/K8hqI37Cvoc="]
+ Received: []
 Tests  1 failed | 10 passed (11)
```

```diff
- const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi;
+ const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script\s*>/gi;
```

```
$ npx vitest run scripts/injectCspHashes.test.ts   # apos a correcao
 Test Files  1 passed (1)
      Tests  11 passed (11)

$ npx vitest run   # suite web completa
 Test Files  80 passed (80)
      Tests  596 passed (596)

$ npx eslint . / npx astro check
0 errors em ambos
```
