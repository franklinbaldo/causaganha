/**
 * Content-Security-Policy content string (#1613, TM-08 in
 * docs/SECURITY_THREAT_MODEL.md), shared by every page's `<meta
 * http-equiv="Content-Security-Policy">` tag so the policy is defined once
 * and cannot drift between `Layout.astro` and the two pages that render
 * their own bare `<html>` document instead of using it
 * (`advogados.astro`/`comparador.astro`, per CLAUDE.md's note that they are
 * the app's only trivial redirect stubs).
 *
 * See the explanatory comment above the `<meta>` tag in `Layout.astro` for
 * the rationale behind each directive.
 */
export const CSP_META_CONTENT =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://archive.org https://comunicaapi.pje.jus.br https://djen-proxy-mhgmawcn3a-rj.a.run.app https://cdn.jsdelivr.net; worker-src 'self' blob: https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self'; form-action 'self';";
