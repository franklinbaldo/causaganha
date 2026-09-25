---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-akb9oz-evidence-codeql-fix-script-closing-tag-regex"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
kind: "review"
reference: "PR #1628 review comment 4102895727 (CodeQL, github-advanced-security[bot]); check run CodeQL (108009738210, 1 high severity alert); web/scripts/injectCspHashes.mjs:28"
summary: "CodeQL sinalizou 2 alertas sucessivos de severidade alta em web/scripts/injectCspHashes.mjs:28 ('Bad HTML filtering regexp'), e uma terceira falha foi encontrada por verificacao manual propria (nao pelo CodeQL) antes de qualquer push. Rodada 1: INLINE_SCRIPT_RE usava /<\\/script>/, nao reconhecendo '</script >' (espaco antes do '>', tag de fechamento valida pelo tokenizer HTML5) -- corrigido para /<\\/script\\s*>/. Rodada 2: CodeQL apontou um caso mais geral, '</script\\t\\n bar>' (conteudo tipo-atributo arbitrario antes do '>', tambem valido -- o tokenizer HTML5 trata qualquer coisa apos o nome da tag de fechamento como atributos ignorados) -- corrigido para o padrao recomendado pela propria CodeQL, /<\\/script[^>]*>/. Rodada 3 (achado proprio, verificacao manual de um build real antes de push): o regex nao tem nocao de comentarios HTML -- o proprio comentario de racional da CSP em Layout.astro usa a frase 'inline <script> tags' em prosa, e o regex casava esse '<script>' literal dentro do comentario como inicio de um script real, consumindo greedily ate o proximo '</script...>' verdadeiro do documento (por sorte, sem engolir nenhum script legitimo no meio, mas produzindo um 4o hash espurio sobre comentario+markup nao relacionado -- inofensivo por nao corresponder a nenhum script real que um navegador executaria, mas uma prova de que o scanner nao reflete como um parser HTML real le o documento). Corrigido removendo comentarios HTML (/<!--[\\s\\S]*?-->/g) do documento antes de escanear por scripts -- so no caminho de deteccao/hash, nao no caminho de reescrita do <meta> CSP (que precisa continuar operando sobre o HTML real). TDD completo: 3 testes novos RED-then-GREEN, um por rodada, cobrindo cada padrao especificamente. Verificado ao vivo com Chromium real apos a correcao final: dist/processo.html volta a ter exatamente os 3 hashes legitimos (nao 4), e o probe de hidratacao (CNJ inválido) continua funcionando sem nenhum erro de console CSP."
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
$ npx vitest run scripts/injectCspHashes.test.ts   # apos as 3 correcoes
 Test Files  1 passed (1)
      Tests  13 passed (13)

$ npx vitest run   # suite web completa
 Test Files  80 passed (80)
      Tests  598 passed (598)

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
