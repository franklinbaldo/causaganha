import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import {
  computeInlineScriptHashes,
  injectHashesIntoCsp,
  rewriteHtmlCsp,
  stripHtmlComments,
} from "./injectCspHashes.mjs";

function sha256Base64(content: string): string {
  return createHash("sha256").update(content, "utf-8").digest("base64");
}

describe("computeInlineScriptHashes (#1613, TM-08 follow-up)", () => {
  it("hashes inline <script> tags (no src) and ignores scripts with a src attribute", () => {
    const html = `
      <script type="module">console.log("a")</script>
      <script type="module" src="/_astro/page.js"></script>
      <script>(()=>{window.x=1})();</script>
    `;
    const hashes = computeInlineScriptHashes(html);
    expect(hashes).toEqual(
      [sha256Base64('console.log("a")'), sha256Base64("(()=>{window.x=1})();")].sort(),
    );
  });

  it("returns an empty array when there are no inline scripts", () => {
    const html = `<script type="module" src="/_astro/page.js"></script>`;
    expect(computeInlineScriptHashes(html)).toEqual([]);
  });

  it("deduplicates identical inline script content across multiple tags", () => {
    const html = `
      <script>console.log("same")</script>
      <script>console.log("same")</script>
    `;
    expect(computeInlineScriptHashes(html)).toEqual([sha256Base64('console.log("same")')]);
  });

  it("skips empty inline scripts (no content to hash)", () => {
    const html = `<script type="module"></script>`;
    expect(computeInlineScriptHashes(html)).toEqual([]);
  });

  it("ignores literal '<script>' text inside an HTML comment (found live: Layout.astro's own CSP rationale comment mentions '<script> tags' in prose)", () => {
    const html = `
      <!-- This comment talks about inline <script> tags in prose, never a
           real element -- a browser never parses comment contents as HTML. -->
      <script>console.log("real")</script>
    `;
    expect(computeInlineScriptHashes(html)).toEqual([sha256Base64('console.log("real")')]);
  });

  it("recognizes a closing tag with whitespace before '>' (valid HTML5, flagged by CodeQL js/bad-tag-filter)", () => {
    // </script > is a valid closing tag per the HTML5 tokenizer. A regexp
    // that only matches the exact literal "</script>" fails to find this
    // boundary and instead keeps scanning for the next literal "</script>"
    // in the document, silently merging unrelated content into the hash.
    const html = `<script>console.log("a")</script ><p>not part of the script</p>`;
    expect(computeInlineScriptHashes(html)).toEqual([sha256Base64('console.log("a")')]);
  });

  it("recognizes a closing tag with junk/attribute-like content before '>' (also valid HTML5)", () => {
    // The HTML5 tokenizer parses an end tag's name ("script"), then any
    // following bytes up to '>' as (invalid, ignored) attributes -- the
    // element still ends there. </script\t\n bar> is exactly this case,
    // and the CodeQL-recommended fix for this query class is </script[^>]*>.
    const html = `<script>console.log("b")</script\t\n bar><p>outside</p>`;
    expect(computeInlineScriptHashes(html)).toEqual([sha256Base64('console.log("b")')]);
  });
});

describe("stripHtmlComments (#1613, TM-08 follow-up; CodeQL js/incomplete-sanitization)", () => {
  it("never leaves a literal '<!--' behind, even for overlapping/malformed markers that defeat a single non-looped replace() pass", () => {
    // A single, non-repeated `.replace(HTML_COMMENT_RE, "")` call over this
    // exact input strips only the inner "<!-- -->" pair and leaves the
    // outer "<!-- -->" behind untouched (verified independently: the naive
    // one-pass strip of "<!-<!-- --><x>- -->" yields "<!-- --><x>-->", a
    // *result that still contains a literal '<!--'* -- exactly the
    // CodeQL js/incomplete-sanitization finding this function must not
    // reproduce). Stripping must repeat until the string stops changing.
    const html = "<!-<!-- --><script>console.log(\"c\")</script>- -->";
    expect(stripHtmlComments(html)).not.toContain("<!--");
  });

  it("removes well-formed comments completely, including several in sequence", () => {
    const html = "a<!-- one -->b<!-- two -->c";
    expect(stripHtmlComments(html)).toBe("abc");
  });
});

describe("injectHashesIntoCsp (#1613, TM-08 follow-up)", () => {
  it("appends sha256 hash tokens to the script-src directive", () => {
    const csp =
      "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none';";
    const result = injectHashesIntoCsp(csp, ["AAAA", "BBBB"]);
    expect(result).toContain("script-src 'self' 'sha256-AAAA' 'sha256-BBBB';");
    // Other directives untouched.
    expect(result).toContain("style-src 'self' 'unsafe-inline';");
    expect(result).toContain("object-src 'none';");
  });

  it("is idempotent: running twice does not duplicate hash tokens", () => {
    const csp = "default-src 'self'; script-src 'self';";
    const once = injectHashesIntoCsp(csp, ["AAAA"]);
    const twice = injectHashesIntoCsp(once, ["AAAA"]);
    expect(twice).toBe(once);
    expect(twice.match(/sha256-AAAA/g)).toHaveLength(1);
  });

  it("never adds 'unsafe-inline' or 'unsafe-eval' to script-src", () => {
    const csp = "script-src 'self';";
    const result = injectHashesIntoCsp(csp, ["AAAA"]);
    expect(result).not.toContain("unsafe-inline");
    expect(result).not.toContain("unsafe-eval");
  });

  it("returns the csp unchanged when given no hashes", () => {
    const csp = "default-src 'self'; script-src 'self';";
    expect(injectHashesIntoCsp(csp, [])).toBe(csp);
  });
});

describe("rewriteHtmlCsp (#1613, TM-08 follow-up)", () => {
  it("finds the CSP meta tag in a full HTML document and rewrites only its content attribute", () => {
    const html = `<!doctype html><html><head>
      <meta charset="UTF-8" />
      <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; object-src 'none';" />
    </head><body>
      <script>console.log("hydrate")</script>
    </body></html>`;
    const rewritten = rewriteHtmlCsp(html);
    const expectedHash = sha256Base64('console.log("hydrate")');
    expect(rewritten).toContain(`'sha256-${expectedHash}'`);
    // The rest of the document is untouched.
    expect(rewritten).toContain('<meta charset="UTF-8" />');
    expect(rewritten).toContain('console.log("hydrate")');
  });

  it("throws a clear error when no CSP meta tag is present (fail closed, never ship without one)", () => {
    const html = `<!doctype html><html><head></head><body></body></html>`;
    expect(() => rewriteHtmlCsp(html)).toThrow(/Content-Security-Policy/);
  });
});
