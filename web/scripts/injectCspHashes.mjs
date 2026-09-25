/**
 * Post-build CSP hardening (#1613 follow-up, TM-08 in docs/SECURITY_THREAT_MODEL.md).
 *
 * Astro's own client-hydration runtime (the `astro-island` bootstrap and the
 * `astro:transitions` ClientRouter Layout.astro uses) injects a handful of
 * small inline `<script>` tags into every built page that has a hydrated
 * island. CSP_META_CONTENT's `script-src 'self'` has no `'unsafe-inline'`,
 * so a browser refuses those scripts outright and the page never hydrates
 * (confirmed live: ProcessoLookup.svelte never shows its "CNJ inválido"
 * validation message under the plain policy).
 *
 * The fix is NOT 'unsafe-inline' (that reopens the exact XSS vector #1613
 * closed) and NOT a nonce (a static site serves the same HTML file to every
 * visitor, so a build-time nonce would be reused forever and provide no
 * real protection). It's a SHA-256 hash allowlist: CSP permits a specific
 * inline script by the hash of its exact byte content. Since this list is
 * computed here, after every build, from the actual build output, it can
 * never drift silently out of sync the way a hand-maintained hash list
 * would after an Astro/Vite upgrade changes the runtime's bundled bytes.
 *
 * Run automatically via package.json's `postbuild` script, after `astro build`.
 */
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const INLINE_SCRIPT_RE = /<script(\s[^>]*)?>([\s\S]*?)<\/script[^>]*>/gi;
const HAS_SRC_ATTR_RE = /\bsrc\s*=/i;
const HTML_COMMENT_RE = /<!--[\s\S]*?-->/g;
const CSP_META_RE =
  /(<meta\s+http-equiv="Content-Security-Policy"\s+content=")([^"]*)("\s*\/?>)/i;

/**
 * Removes every HTML comment, including cases a single non-looped
 * `replace()` pass would miss: e.g. "<!-<!-- --><x>- -->" strips only the
 * inner "<!-- -->" in one pass, leaving a literal "<!--" behind (CodeQL
 * js/incomplete-sanitization). Repeats until the string stops changing so
 * no such marker can survive.
 * @param {string} html @returns {string}
 */
export function stripHtmlComments(html) {
  let stripped = html;
  let previous;
  do {
    previous = stripped;
    stripped = stripped.replace(HTML_COMMENT_RE, "");
  } while (stripped !== previous);
  return stripped;
}

/** @param {string} html @returns {string[]} sorted, deduplicated sha256-base64 hashes */
export function computeInlineScriptHashes(html) {
  // A browser never parses HTML comment contents as markup, so a literal
  // "<script>" appearing in a documentation comment (this file's own CSP
  // rationale comment in Layout.astro talks about "inline <script> tags"
  // in prose) must not be treated as a real element boundary. Strip
  // comments first, matching the scanner to what a real parser sees.
  const withoutComments = stripHtmlComments(html);
  const hashes = new Set();
  for (const match of withoutComments.matchAll(INLINE_SCRIPT_RE)) {
    const attrs = match[1] ?? "";
    const content = match[2];
    if (HAS_SRC_ATTR_RE.test(attrs)) continue; // external script, src= is covered by 'self'
    if (!content) continue; // nothing to hash, nothing to allow
    hashes.add(createHash("sha256").update(content, "utf-8").digest("base64"));
  }
  return [...hashes].sort();
}

/** @param {string} csp @param {string[]} hashes @returns {string} */
export function injectHashesIntoCsp(csp, hashes) {
  if (hashes.length === 0) return csp;
  return csp.replace(/script-src ([^;]+);/, (full, existing) => {
    const tokens = existing.trim().split(/\s+/);
    for (const hash of hashes) {
      const token = `'sha256-${hash}'`;
      if (!tokens.includes(token)) tokens.push(token);
    }
    return `script-src ${tokens.join(" ")};`;
  });
}

/** @param {string} html @returns {string} */
export function rewriteHtmlCsp(html) {
  const match = html.match(CSP_META_RE);
  if (!match) {
    throw new Error(
      "No <meta http-equiv=\"Content-Security-Policy\"> tag found — refusing to ship a page with no CSP.",
    );
  }
  const hashes = computeInlineScriptHashes(html);
  const newContent = injectHashesIntoCsp(match[2], hashes);
  return html.slice(0, match.index) + match[1] + newContent + match[3] + html.slice(match.index + match[0].length);
}

function walkHtmlFiles(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) walkHtmlFiles(full, out);
    else if (entry.isFile() && entry.name.endsWith(".html")) out.push(full);
  }
  return out;
}

function main() {
  const distDir = fileURLToPath(new URL("../dist", import.meta.url));
  const files = walkHtmlFiles(distDir);
  let rewritten = 0;
  for (const file of files) {
    const html = readFileSync(file, "utf-8");
    const next = rewriteHtmlCsp(html);
    if (next !== html) {
      writeFileSync(file, next);
      rewritten += 1;
    }
  }
  console.log(`injectCspHashes: patched CSP script-src hashes into ${rewritten}/${files.length} page(s).`);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
