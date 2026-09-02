import { cleanup, screen, waitFor } from '@testing-library/svelte/pure';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AnnualCoverageMonitorRaw from './AnnualCoverageMonitor.svelte';
import { render } from './__steps__/shared';

const AnnualCoverageMonitor = AnnualCoverageMonitorRaw as unknown as Parameters<typeof render>[0];

function unavailableResponse() {
  return new Response(JSON.stringify({ message: 'Service Unavailable' }), {
    status: 503,
    headers: { 'content-type': 'application/json' },
  });
}

describe('AnnualCoverageMonitor — source-unavailable state', () => {
  beforeEach(() => {
    cleanup();
    vi.restoreAllMocks();
    // The IA Advanced Search API is unreachable — `fetchAllTribunalMetadata`
    // never throws; it resolves one row per tribunal, all with `notFound: true`
    // and the same `error` message (a single request covers every tribunal).
    global.fetch = vi.fn().mockResolvedValue(unavailableResponse()) as unknown as typeof fetch;
  });

  afterEach(() => {
    cleanup();
  });

  it(
    'never presents a fetch failure as confirmed-absent coverage, and offers retry',
    async () => {
      render(AnnualCoverageMonitor);

      await waitFor(
        () => {
          expect(screen.getByText('Não foi possível verificar a cobertura.')).toBeTruthy();
        },
        { timeout: 8000 },
      );

      expect(screen.getByText(/não confirma ausência de arquivos/i)).toBeTruthy();

      // Must never render the table as if 0%/N/A for every tribunal were a
      // confirmed verdict of missing coverage — that conflates "fonte
      // indisponível" with "ausência" (issue #907).
      expect(screen.queryByText('N/A')).toBeNull();
      expect(screen.queryByRole('table')).toBeNull();

      expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeTruthy();
    },
    10000,
  );
});
