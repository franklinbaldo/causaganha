import { describe, expect, it } from 'vitest';

import { DIRECT_ARCHIVE_DOWNLOAD_BASE, resolveArchiveDownloadBase } from './archiveProxyBase';

describe('resolveArchiveDownloadBase', () => {
  it('defaults to archive.org direct downloads when no proxy is configured', () => {
    expect(resolveArchiveDownloadBase(undefined)).toBe(DIRECT_ARCHIVE_DOWNLOAD_BASE);
    expect(resolveArchiveDownloadBase(null)).toBe(DIRECT_ARCHIVE_DOWNLOAD_BASE);
    expect(resolveArchiveDownloadBase('')).toBe(DIRECT_ARCHIVE_DOWNLOAD_BASE);
    expect(resolveArchiveDownloadBase('   ')).toBe(DIRECT_ARCHIVE_DOWNLOAD_BASE);
  });

  it('routes through a configured proxy origin, appending /download', () => {
    expect(resolveArchiveDownloadBase('https://archive-cors-proxy.example.workers.dev')).toBe(
      'https://archive-cors-proxy.example.workers.dev/download',
    );
  });

  it('strips a trailing slash from the configured proxy origin', () => {
    expect(resolveArchiveDownloadBase('https://archive-cors-proxy.example.workers.dev/')).toBe(
      'https://archive-cors-proxy.example.workers.dev/download',
    );
  });
});
