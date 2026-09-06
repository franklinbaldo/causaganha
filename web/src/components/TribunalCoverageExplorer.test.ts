import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TribunalCoverageExplorer from './TribunalCoverageExplorer.svelte';
import type { TribunalCalendarRow } from '../lib/tribunalCoverageDrilldown';

const ROWS_BY_TRIBUNAL: Record<string, TribunalCalendarRow[]> = {
  TJRO: [
    { tribunal: 'TJRO', date: '2026-01-01', status: 'uploaded' },
    { tribunal: 'TJRO', date: '2026-01-02', status: 'uploaded' },
    { tribunal: 'TJRO', date: '2026-01-03', status: 'absent' },
  ],
  TJSP: [{ tribunal: 'TJSP', date: '2026-06-01', status: 'absent' }],
};

const TRIBUNALS = ['TJRO', 'TJSP'];

function mockFetch(rowsByTribunal: Record<string, TribunalCalendarRow[]> = ROWS_BY_TRIBUNAL) {
  const fetchMock = vi.fn((input: string) => {
    const match = /tribunal_calendar_by_tribunal\/([a-z0-9]+)\.json$/.exec(String(input));
    const code = match ? match[1].toUpperCase() : '';
    const rows = rowsByTribunal[code] ?? [];
    return Promise.resolve(
      new Response(JSON.stringify(rows), { status: 200, headers: { 'content-type': 'application/json' } }),
    );
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

beforeEach(() => {
  window.history.replaceState(null, '', '/stats');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('TribunalCoverageExplorer', () => {
  it('fetches only the selected tribunal partition, never the full/global calendar contract', async () => {
    const fetchMock = mockFetch();

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    for (const call of fetchMock.mock.calls) {
      const url = String(call[0]);
      expect(url).toMatch(/tribunal_calendar_by_tribunal\/tjro\.json$/);
      expect(url).not.toMatch(/\/data\/tribunal_calendar\.json$/);
    }
  });

  it('shows the uploaded/absent breakdown for the default tribunal and period once loaded', async () => {
    mockFetch();

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    await waitFor(() => {
      expect(screen.getByText(/2 dias preservados/i)).toBeInTheDocument();
      expect(screen.getByText(/1 dia com ausência confirmada/i)).toBeInTheDocument();
    });
  });

  it('shows a not-enough-evidence message instead of 0% when the period has no observed day', async () => {
    mockFetch();

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJSP',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-02',
    });

    await waitFor(() => {
      expect(screen.getByText(/sem evidência suficiente neste período/i)).toBeInTheDocument();
    });
  });

  it('refetches only the newly selected tribunal partition when the selection changes', async () => {
    const fetchMock = mockFetch();

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const select = screen.getByLabelText(/tribunal/i) as HTMLSelectElement;
    await fireEvent.change(select, { target: { value: 'TJSP' } });

    await waitFor(() => {
      expect(screen.getByText(/sem evidência suficiente neste período/i)).toBeInTheDocument();
    });

    const tjspCalls = fetchMock.mock.calls.filter(call => String(call[0]).includes('/tjsp.json'));
    expect(tjspCalls.length).toBeGreaterThan(0);
  });

  it('shows a load-error message instead of a silent/misleading empty state when the partition fetch fails', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('network down')) as unknown as typeof fetch;

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    await waitFor(() => {
      expect(screen.getByText(/não foi possível carregar/i)).toBeInTheDocument();
    });
  });

  it('reflects the current selection in the URL querystring', async () => {
    mockFetch();

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    const select = screen.getByLabelText(/tribunal/i) as HTMLSelectElement;
    await fireEvent.change(select, { target: { value: 'TJSP' } });

    await waitFor(() => {
      const params = new URLSearchParams(window.location.search);
      expect(params.get('tribunal')).toBe('TJSP');
    });
  });

  it('links to the full per-tribunal calendar page', () => {
    mockFetch();

    render(TribunalCoverageExplorer, {
      tribunals: TRIBUNALS,
      publicBase: '/',
      initialTribunal: 'TJRO',
      initialStart: '2026-01-01',
      initialEnd: '2026-01-03',
    });

    const link = screen.getByRole('link', { name: /ver calendário completo/i }) as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/publicacoes/tjro');
  });

  describe('copyQueryLink', () => {
    function stubClipboard(writeText: (text: string) => Promise<void>) {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText },
        configurable: true,
      });
    }

    it('copies the current page URL, including the drilldown query, and confirms success', async () => {
      mockFetch();
      const writeText = vi.fn().mockResolvedValue(undefined);
      stubClipboard(writeText);

      render(TribunalCoverageExplorer, {
        tribunals: TRIBUNALS,
        publicBase: '/',
        initialTribunal: 'TJRO',
        initialStart: '2026-01-01',
        initialEnd: '2026-01-03',
      });

      const select = screen.getByLabelText(/tribunal/i) as HTMLSelectElement;
      await fireEvent.change(select, { target: { value: 'TJSP' } });

      const copyButton = screen.getByRole('button', { name: /copiar link desta consulta/i });
      await fireEvent.click(copyButton);

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledTimes(1);
      });
      const copiedUrl = writeText.mock.calls[0][0] as string;
      expect(copiedUrl).toContain(window.location.pathname);
      expect(new URL(copiedUrl).searchParams.get('tribunal')).toBe('TJSP');

      await waitFor(() => {
        expect(screen.getByText(/link copiado/i)).toBeInTheDocument();
      });
    });

    it('falls back to a manual-copy message when the Clipboard API rejects', async () => {
      mockFetch();
      stubClipboard(vi.fn().mockRejectedValue(new Error('permission denied')));

      render(TribunalCoverageExplorer, {
        tribunals: TRIBUNALS,
        publicBase: '/',
        initialTribunal: 'TJRO',
        initialStart: '2026-01-01',
        initialEnd: '2026-01-03',
      });

      const copyButton = screen.getByRole('button', { name: /copiar link desta consulta/i });
      await fireEvent.click(copyButton);

      await waitFor(() => {
        expect(screen.getByText(/não foi possível copiar automaticamente/i)).toBeInTheDocument();
      });
    });

    it('clears a prior copy confirmation once the query changes again', async () => {
      mockFetch();
      stubClipboard(vi.fn().mockResolvedValue(undefined));

      render(TribunalCoverageExplorer, {
        tribunals: TRIBUNALS,
        publicBase: '/',
        initialTribunal: 'TJRO',
        initialStart: '2026-01-01',
        initialEnd: '2026-01-03',
      });

      const copyButton = screen.getByRole('button', { name: /copiar link desta consulta/i });
      await fireEvent.click(copyButton);
      await waitFor(() => {
        expect(screen.getByText(/link copiado/i)).toBeInTheDocument();
      });

      const select = screen.getByLabelText(/tribunal/i) as HTMLSelectElement;
      await fireEvent.change(select, { target: { value: 'TJSP' } });

      expect(screen.queryByText(/link copiado/i)).not.toBeInTheDocument();
    });
  });
});
