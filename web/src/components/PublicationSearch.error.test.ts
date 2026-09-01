import { cleanup, fireEvent, screen, waitFor } from '@testing-library/svelte/pure';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PublicationSearchRaw from './PublicationSearch.svelte';
import { render } from './__steps__/shared';
import { clearDjenSearchCache } from '../lib/djen';

const PublicationSearch = PublicationSearchRaw as unknown as Parameters<typeof render>[0];

function backendErrorResponse() {
  return new Response(JSON.stringify({ message: 'Internal Server Error' }), {
    status: 502,
    headers: { 'content-type': 'application/json' },
  });
}

describe('PublicationSearch — source-unavailable state', () => {
  beforeEach(() => {
    cleanup();
    clearDjenSearchCache();
    vi.restoreAllMocks();
    window.history.replaceState({}, '', '/publicacoes');
    // 5xx is a real backend failure (not a rate-limit/validation error), so
    // it retries per the query's own `retry` policy before settling into
    // the 'error' status — see djen-search.steps.ts's 5xx coverage.
    global.fetch = vi.fn().mockResolvedValue(backendErrorResponse()) as unknown as typeof fetch;
  });

  afterEach(() => {
    cleanup();
    clearDjenSearchCache();
  });

  it('never presents a fetch failure as "no results", preserves the query in the URL, and offers the historical archive', async () => {
    render(PublicationSearch);

    const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'contrato' } });
    await fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(
      () => {
        expect(screen.getByText('Não foi possível buscar.')).toBeTruthy();
      },
      { timeout: 8000 },
    );

    // Must never be conflated with a genuine empty result.
    expect(screen.queryByText('Nenhum resultado nesta consulta.')).toBeNull();

    // The query must survive a fetch failure so a reload/shared link doesn't
    // silently lose it (unlike a successful search, which already syncs it).
    expect(window.location.search).toContain('texto=contrato');

    // A source outage should route to the preserved archive instead of a
    // dead end, mirroring the 'ratelimited' state's own historical-archive link.
    const archiveLink = screen.getByRole('button', { name: 'Consultar arquivo histórico' });
    expect(archiveLink.getAttribute('href')).toBe(
      'https://archive.org/details/causaganha-dashboard',
    );
  });
});
