export const DIRECT_ARCHIVE_DOWNLOAD_BASE = 'https://archive.org/download';

/**
 * Resolves the base URL used to build `read_parquet(...)` paths for
 * Internet Archive downloads in DuckDBExplorer.
 *
 * When `proxyBase` is unset (the default today), downloads still target
 * `archive.org` directly — see issue #1482 for why the browser then blocks
 * the read (no `Access-Control-Allow-Origin` on that endpoint). When a
 * proxy base is configured (e.g. a deployed `deployment/archive-cors-proxy`
 * Worker), downloads are routed through it instead, which adds the header.
 */
export function resolveArchiveDownloadBase(proxyBase?: string | null): string {
  const trimmed = proxyBase?.trim();
  if (!trimmed) return DIRECT_ARCHIVE_DOWNLOAD_BASE;
  return `${trimmed.replace(/\/+$/, '')}/download`;
}
