---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-codeql-fix-script-closing-tag-regex"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "review"
reference: "PR #1628 review comment 4102895727 (CodeQL, github-advanced-security[bot]); check run CodeQL (108009738210, 1 high severity alert); web/scripts/injectCspHashes.mjs:28"
summary: "CodeQL sinalizou 3 alertas sucessivos de severidade alta em web/scripts/injectCspHashes.mjs (2 na mesma linha 28, 1 na linha 41), e uma quarta falha foi encontrada por verificacao manual propria (nao pelo CodeQL) antes de qualquer push. Rodada 1: INLINE_SCRIPT_RE usava /<\\/script>/, nao reconhecendo '</script >' (espaco antes do '>', tag de fechamento valida pelo tokenizer HTML5) -- corrigido para /<\\/script\\s*>/. Rodada 2: CodeQL apontou um caso mais geral, '</script\\t\\n bar>' (conteudo tipo-atributo arbitrario antes do '>', tambem valido) -- corrigido para o padrao recomendado pela propria CodeQL, /<\\/script[^>]*>/. Rodada 3 (achado proprio, verificacao manual de um build real antes de push): o regex nao tem nocao de comentarios HTML -- o proprio comentario de racional da CSP em Layout.astro usa a frase 'inline <script> tags' em prosa, e o regex casava esse '<script>' literal dentro do comentario, consumindo ate o proximo '</script...>' verdadeiro e produzindo um 4o hash espurio (inofensivo, mas prova de que o scanner nao lia o documento como um parser real). Corrigido removendo comentarios HTML antes de escanear. Rodada 4 (CodeQL, 'Incomplete multi-character sanitization', apos o push da rodada 3): a remocao de comentarios usava uma unica chamada html.replace(HTML_COMMENT_RE, \"\") -- confirmado programaticamente (node -e) que uma unica passada sobre a entrada '<!-<!-- --><x>- -->' remove so o par interno '<!-- -->' e deixa o par externo '<!-- -->' intacto no resultado, uma string que ainda contem '<!--' literal. Corrigido extraindo stripHtmlComments(html) como funcao propria testada isoladamente, que repete a substituicao ate o resultado estabilizar (loop de ponto fixo) -- garantindo que nenhuma sequencia remanescente de '<!--' sobrevive, exatamente a alegacao do alerta CodeQL. TDD completo: 5 testes novos RED-then-GREEN no total (1 por rodada 1/2/3, 2 para a rodada 4: o caso adversarial que derrota uma unica passada, e um caso de multiplos comentarios bem formados em sequencia). Verificado ao vivo com Chromium real apos todas as correcoes: dist/processo.html continua com exatamente os 3 hashes legitimos, hidratacao funciona, 0 erros de console CSP."
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
# rodada 1 (CodeQL, </script >)
- const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script>/gi;
+ const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script\s*>/gi;

# rodada 2 (CodeQL, </script\t\n bar>)
- const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script\s*>/gi;
+ const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script[^>]*>/gi;

# rodada 3 (achado proprio, comentarios HTML)
+ const HTML_COMMENT_RE = /<!--[\s\S]*?-->/g;
  export function computeInlineScriptHashes(html) {
+   const withoutComments = html.replace(HTML_COMMENT_RE, "");
    const hashes = new Set();
-   for (const match of html.matchAll(INLINE_SCRIPT_RE)) {
+   for (const match of withoutComments.matchAll(INLINE_SCRIPT_RE)) {
```

```
$ npx vitest run scripts/injectCspHashes.test.ts   # apos as 4 correcoes
 Test Files  1 passed (1)
      Tests  15 passed (15)

$ npx vitest run   # suite web completa
 Test Files  80 passed (80)
      Tests  600 passed (600)

$ npx eslint . / npx astro check
0 errors em ambos

$ rm -rf dist && npm run build   # com fixtures sinteticas
injectCspHashes: patched CSP script-src hashes into 103/111 page(s).
$ grep -o "script-src[^;]*;" dist/processo.html
script-src 'self' 'sha256-Ya0pUYrC7nM5Cn/056TyVuEiz6dFGrzmkWzgON0pF0U='
  'sha256-eIXWvAmxkr251LJZkjniEK5LcPF3NkapbJepohwYRIc='
  'sha256-ywDn4AkgLzJyrJIM2y/daMBkO4v1+WOHLIVFHbnbfH0=';
# de volta a exatamente 3 hashes legitimos (a rodada 2, sem a rodada 3,
# tinha produzido 4 -- o hash espurio do comentario)

$ node probe.mjs   # Chromium real, mesma pagina
FOUND: CNJ inválido text appeared   # sem nenhum erro de console CSP
```
