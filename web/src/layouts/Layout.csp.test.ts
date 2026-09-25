import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { CSP_META_CONTENT } from '../lib/csp';

const __dirname = dirname(fileURLToPath(import.meta.url));

// The app is a fully static GitHub Pages build (astro.config.mjs:
// `output: 'static'`) — there is no server to set HTTP response headers, so
// the policy can only be delivered via a `<meta http-equiv>` tag. Per the
// CSP spec, `frame-ancestors`, `sandbox` and `report-uri`/`report-to` are
// silently ignored when delivered this way, so they are deliberately not
// asserted here (see docs/SECURITY_THREAT_MODEL.md TM-08 and the round's
// AgentDecision for the documented gap).
function directive(csp: string, name: string): string[] {
  const re = new RegExp(`(?:^|;)\\s*${name}\\s+([^;]+)`);
  const match = csp.match(re);
  if (!match) throw new Error(`Directive "${name}" not found in CSP: ${csp}`);
  return match[1].trim().split(/\s+/);
}

// Layout.astro wraps every "real" page. advogados.astro and comparador.astro
// render their own bare <html> document instead of using Layout.astro (they
// are the app's only trivial redirect stubs, per CLAUDE.md), so each needs
// its own copy of the <meta> tag — this list guards that neither page loses
// it silently, e.g. during a refactor that touches only Layout.astro.
const PAGES_REQUIRING_CSP = [
  resolve(__dirname, 'Layout.astro'),
  resolve(__dirname, '../pages/advogados.astro'),
  resolve(__dirname, '../pages/comparador.astro'),
];

describe('Content-Security-Policy is wired into every page (#1613, TM-08)', () => {
  for (const path of PAGES_REQUIRING_CSP) {
    it(`${path.split('/').slice(-1)[0]} renders the shared CSP meta tag`, () => {
      const source = readFileSync(path, 'utf-8');
      expect(source).toMatch(/<meta\s+http-equiv="Content-Security-Policy"\s+content=\{CSP_META_CONTENT\}\s*\/>/);
      expect(source).toMatch(/import\s+\{\s*CSP_META_CONTENT\s*\}\s+from\s+['"].*lib\/csp['"]/);
    });
  }
});

describe('CSP_META_CONTENT policy (#1613, TM-08)', () => {
  it('script-src is self-only: no unsafe-inline, no unsafe-eval, no wildcard', () => {
    const scriptSrc = directive(CSP_META_CONTENT, 'script-src');
    expect(scriptSrc).toContain("'self'");
    expect(scriptSrc).not.toContain("'unsafe-inline'");
    expect(scriptSrc).not.toContain("'unsafe-eval'");
    expect(scriptSrc).not.toContain('*');
  });

  it('object-src is none (no plugins/legacy embeds)', () => {
    expect(directive(CSP_META_CONTENT, 'object-src')).toEqual(["'none'"]);
  });

  it('base-uri and form-action are locked to self', () => {
    expect(directive(CSP_META_CONTENT, 'base-uri')).toEqual(["'self'"]);
    expect(directive(CSP_META_CONTENT, 'form-action')).toEqual(["'self'"]);
  });

  it('connect-src is a closed allowlist covering every host the app actually fetches', () => {
    const connectSrc = directive(CSP_META_CONTENT, 'connect-src');
    expect(connectSrc).toContain("'self'");
    expect(connectSrc).toContain('https://archive.org');
    expect(connectSrc).toContain('https://comunicaapi.pje.jus.br');
    expect(connectSrc).toContain('https://djen-proxy-mhgmawcn3a-rj.a.run.app');
    expect(connectSrc).toContain('https://cdn.jsdelivr.net');
    expect(connectSrc).not.toContain('*');
  });

  it('worker-src allows only self, blob: (DuckDB-WASM fallback) and the jsDelivr CDN it loads from', () => {
    const workerSrc = directive(CSP_META_CONTENT, 'worker-src');
    expect(workerSrc).toContain("'self'");
    expect(workerSrc).toContain('blob:');
    expect(workerSrc).toContain('https://cdn.jsdelivr.net');
    expect(workerSrc).not.toContain('*');
  });

  it('no directive contains a bare wildcard origin', () => {
    const directives = CSP_META_CONTENT.split(';').map((d) => d.trim()).filter(Boolean);
    for (const d of directives) {
      const [name, ...values] = d.split(/\s+/);
      expect(values, `directive "${name}" must not allow a bare "*" origin`).not.toContain('*');
    }
  });

  it('style-src stays self + unsafe-inline (documented tradeoff, see AgentDecision) and never a remote host', () => {
    // Svelte's scoped-style mechanism (mandated by CLAUDE.md's CSS token
    // boundary section) emits static <style> blocks and style="..." attrs
    // directly into every server-rendered page — verified against the
    // actual `npm run build` output for /processo, /agentes, /explorador,
    // /minhas-consultas. None of that content is user-controlled: djen.ts's
    // sanitizeHtml() (FORBID_TAGS: ["style"], FORBID_ATTR: ["style"]) means
    // untrusted judicial text can never reach a <style> sink. 'unsafe-inline'
    // for style-src is therefore a deliberate, bounded exception, never
    // extended to script-src.
    const styleSrc = directive(CSP_META_CONTENT, 'style-src');
    expect(styleSrc).toContain("'self'");
    expect(styleSrc).toContain("'unsafe-inline'");
    expect(styleSrc.some((v) => v.startsWith('http'))).toBe(false);
  });
});
