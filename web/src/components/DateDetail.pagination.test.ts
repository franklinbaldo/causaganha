import { cleanup, screen, waitFor } from '@testing-library/svelte/pure';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import DateDetailRaw from './DateDetail.svelte';
import { render } from './__steps__/shared';

const DateDetail = DateDetailRaw as unknown as Parameters<typeof render>[0];

// A tribunal/date pair with more shard files than the page-discovery probe
// used to check for (see this round's AgentGoal): DJEN pages are
// PUBS_PER_PAGE=1000 publications each, so 35 pages means 35,000
// publications for this single (tribunal, date) -- large but real for a
// high-volume tribunal or a backlog-catch-up day.
const TOTAL_REAL_PAGES = 35;

function pageNumberFromUrl(url: string): number | null {
  const match = url.match(/_(\d+)\.json$/);
  return match ? Number(match[1]) : null;
}

describe('DateDetail — page discovery beyond the historical 30-page probe', () => {
  beforeEach(() => {
    cleanup();
    global.fetch = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const url = String(input);
      if (url.includes('archive.org/metadata/')) {
        return new Response(JSON.stringify({ files: [] }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        });
      }
      const pageNum = pageNumberFromUrl(url);
      const exists = pageNum !== null && pageNum <= TOTAL_REAL_PAGES;
      const method = init.method ?? 'GET';
      if (method === 'HEAD') {
        return new Response(null, { status: exists ? 200 : 404 });
      }
      return new Response(exists ? '[]' : 'not found', {
        status: exists ? 200 : 404,
        headers: { 'content-type': 'application/json' },
      });
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    cleanup();
  });

  it(
    'discovers all 35 pages, not just the first 30',
    async () => {
      render(DateDetail, { tribunalCode: 'tjro', dateStr: '2026-01-05' });

      await waitFor(
        () => {
          expect(screen.getByText(`${TOTAL_REAL_PAGES} pág.`)).toBeTruthy();
        },
        { timeout: 8000 },
      );

      expect(screen.queryByText('30 pág.')).toBeNull();
    },
    10000,
  );
});
