/**
 * OG image path for a tribunal's `/publicacoes/[tribunal]` page.
 *
 * The SVG at `og/{tribunal}.svg` is only ever written to `public/og/` during
 * a production build, and only when the tribunal has at least one archived
 * ZIP (see `[tribunal].astro`) — a non-PROD build or a tribunal with zero
 * coverage never produces that file. Returning its path unconditionally
 * would point `og:image`/`twitter:image` at a URL that 404s; returning
 * `null` lets the caller omit `ogImage` so `Layout.astro` falls back to the
 * site-wide `og-image.png` instead.
 */
export function tribunalOgImagePath(
  tribunalCode: string,
  zipCount: number,
  isProdBuild: boolean,
): string | null {
  if (!isProdBuild || zipCount <= 0) return null;
  return `og/${tribunalCode.toLowerCase()}.svg`;
}
