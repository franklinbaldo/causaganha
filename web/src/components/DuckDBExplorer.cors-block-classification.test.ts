import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getDuckDB } from '../lib/duckdbSingleton';
import DuckDBExplorer from './DuckDBExplorer.svelte';

vi.mock('../lib/duckdbSingleton', () => ({ getDuckDB: vi.fn() }));

const START_DATES = { TJRO: '2024-01-01' };
const CURRENT_YEAR = new Date().getUTCFullYear();

async function selectTribunalAndYear() {
  const tribunalSelect = screen.getByLabelText('Tribunal') as HTMLSelectElement;
  await waitFor(() => {
    expect(Array.from(tribunalSelect.options).some((opt) => opt.value === 'TJRO')).toBe(true);
  });
  await fireEvent.change(tribunalSelect, { target: { value: 'TJRO' } });

  const yearSelect = screen.getByLabelText('Ano') as HTMLSelectElement;
  await waitFor(() => {
    expect(Array.from(yearSelect.options).some((opt) => opt.value === String(CURRENT_YEAR))).toBe(true);
  });
  await fireEvent.change(yearSelect, { target: { value: String(CURRENT_YEAR) } });
}

/**
 * Routes fetch by URL shape: tribunal_start_dates.json, the IA metadata
 * endpoint (`/metadata/{id}/files`, which archive.org actually sends CORS
 * headers for), and the IA download endpoint (`/download/{id}/...`, which
 * archive.org does NOT send CORS headers for -- see issue #1482). A real
 * cross-origin browser fetch against the download endpoint rejects with a
 * TypeError; it never resolves with a readable response.
 */
function mockArchiveFetch({
  downloadOutcome,
}: {
  downloadOutcome: 'cors-blocked' | 'reachable';
}) {
  const fetchMock = vi.fn((input: string) => {
    const url = String(input);
    if (url.endsWith('tribunal_start_dates.json')) {
      return Promise.resolve(
        new Response(JSON.stringify(START_DATES), { status: 200, headers: { 'content-type': 'application/json' } }),
      );
    }
    if (url.includes('/metadata/')) {
      return Promise.resolve(
        new Response(JSON.stringify({ result: [{ name: 'comunicacoes.parquet', size: 100 }] }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      );
    }
    // /download/... probe
    if (downloadOutcome === 'cors-blocked') {
      return Promise.reject(new TypeError('Failed to fetch'));
    }
    return Promise.resolve(new Response(new Uint8Array([0]), { status: 206 }));
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

beforeEach(() => {
  vi.mocked(getDuckDB).mockResolvedValue({ db: {}, conn: {} } as never);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('DuckDBExplorer download-endpoint CORS-block classification', () => {
  it('classifies a rejected download-endpoint probe as a distinct, non-transient CORS-block state', async () => {
    mockArchiveFetch({ downloadOutcome: 'cors-blocked' });

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/CORS/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/1482/)).toBeInTheDocument();
    expect(screen.queryByText(/instabilidade temporária/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/não encontrado no Internet Archive/i)).not.toBeInTheDocument();
  });

  it('does not report a CORS block when the download-endpoint probe resolves, even with a non-2xx status', async () => {
    mockArchiveFetch({ downloadOutcome: 'reachable' });

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    const textarea = screen.getByLabelText('Editor SQL') as HTMLTextAreaElement;
    await waitFor(() => {
      expect(textarea).not.toBeDisabled();
    });
    expect(screen.queryByText(/CORS/i)).not.toBeInTheDocument();
  });

  it('blocks runQuery() with the CORS-block message instead of attempting the query', async () => {
    mockArchiveFetch({ downloadOutcome: 'cors-blocked' });
    const query = vi.fn();
    vi.mocked(getDuckDB).mockResolvedValue({ db: {}, conn: { query } } as never);

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/CORS/i)).toBeInTheDocument();
    });

    const textarea = screen.getByLabelText('Editor SQL') as HTMLTextAreaElement;
    expect(textarea).toBeDisabled();
    expect(query).not.toHaveBeenCalled();
  });

  it('does not offer a "tentar novamente" retry affordance for a CORS block, since retrying cannot fix it', async () => {
    mockArchiveFetch({ downloadOutcome: 'cors-blocked' });

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/CORS/i)).toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /tentar (verificar )?novamente/i })).not.toBeInTheDocument();
  });
});
