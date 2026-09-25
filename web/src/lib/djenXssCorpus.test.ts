import { describe, expect, it } from "vitest";
import { normalizePublication } from "./djen";

/**
 * Regression floor for #1613 (TM-08): sanitizeHtml() in djen.ts is the sole
 * control standing between raw DJEN publication text (a third party
 * partially controls this content) and {@html} in PublicationReader.svelte /
 * PublicationDetailPanel.svelte. This corpus pins down the current behavior
 * so a DOMPurify config regression, dependency downgrade, or refactor that
 * weakens the sanitizer trips a test instead of shipping silently.
 */
function render(texto: string): string {
  const pub = normalizePublication({ texto } as never);
  expect(pub.textoRender?.kind).toBe("html");
  return pub.textoRender?.content ?? "";
}

const DANGEROUS_PATTERNS: Array<[string, RegExp]> = [
  ["script tag", /<script/i],
  ["event handler attribute", /\bon\w+\s*=/i],
  ["javascript: URI", /javascript:/i],
  ["iframe", /<iframe/i],
  ["object embed", /<object/i],
  ["embed tag", /<embed/i],
  ["style attribute", /\sstyle\s*=/i],
  ["formaction attribute", /formaction/i],
];

function expectInert(html: string) {
  for (const [label, pattern] of DANGEROUS_PATTERNS) {
    expect(html, `expected no ${label} in sanitized output: ${html}`).not.toMatch(pattern);
  }
}

describe("XSS corpus regression floor for sanitizeHtml (#1613, TM-08)", () => {
  it("strips a <script> tag while preserving sibling benign markup", () => {
    const html = render("<script>alert(document.cookie)</script><p>Intimação publicada.</p>");
    expectInert(html);
    expect(html).toContain("Intimação publicada.");
  });

  it("strips onerror from an <img> tag", () => {
    const html = render('<img src="x" onerror="alert(1)">texto');
    expectInert(html);
  });

  it("strips onload from an <svg> element", () => {
    const html = render('<svg onload="alert(1)"><circle/></svg><p>ok</p>');
    expectInert(html);
  });

  it("neutralizes a javascript: href", () => {
    const html = render('<a href="javascript:alert(1)">clique aqui</a>');
    expectInert(html);
  });

  it("neutralizes a mixed-case javascript: href", () => {
    const html = render('<a href="JaVaScRiPt:alert(1)">clique aqui</a>');
    expectInert(html);
  });

  it("strips a style attribute carrying a javascript: url() payload", () => {
    const html = render('<div style="background:url(javascript:alert(1))">texto</div>');
    expectInert(html);
  });

  it("strips an <iframe> entirely", () => {
    const html = render('<iframe src="javascript:alert(1)"></iframe><p>corpo</p>');
    expectInert(html);
    expect(html).toContain("corpo");
  });

  it("strips an <object> tag entirely", () => {
    const html = render('<object data="data:text/html,<script>alert(1)</script>"></object><p>corpo</p>');
    expectInert(html);
    expect(html).toContain("corpo");
  });

  it("strips a formaction attribute on a form control", () => {
    const html = render(
      '<form action="/x"><button formaction="javascript:alert(1)">Enviar</button></form>',
    );
    expectInert(html);
  });

  it("leaves an already-HTML-entity-encoded script as inert literal text, not a live tag", () => {
    const html = render("<p>Texto contendo &lt;script&gt;alert(1)&lt;/script&gt; literal.</p>");
    expectInert(html);
    expect(html).toContain("&lt;script&gt;");
  });

  it("does not strip benign formatting and real links (no false positives)", () => {
    const html = render(
      '<p>Texto <b>normal</b> com <a href="https://tjro.jus.br/doc/1">link oficial</a>.</p>',
    );
    expect(html).toContain("<b>normal</b>");
    expect(html).toContain('href="https://tjro.jus.br/doc/1"');
    expect(html).toContain("link oficial");
  });
});
