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

function mockArchiveFetch(archiveHandler: (url: string) => Promise<Response>) {
  const fetchMock = vi.fn((input: string) => {
    const url = String(input);
    if (url.endsWith('tribunal_start_dates.json')) {
      return Promise.resolve(
        new Response(JSON.stringify(START_DATES), { status: 200, headers: { 'content-type': 'application/json' } }),
      );
    }
    return archiveHandler(url);
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

describe('DuckDBExplorer dataset availability classification', () => {
  it('classifies a 404 from the Internet Archive metadata endpoint as a missing dataset', async () => {
    mockArchiveFetch(() => Promise.resolve(new Response('not found', { status: 404 })));

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/não encontrado no Internet Archive/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/instabilidade temporária/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /tentar verificar novamente/i })).not.toBeInTheDocument();
  });

  it('classifies valid metadata with no parquet files as a missing dataset', async () => {
    mockArchiveFetch(() =>
      Promise.resolve(
        new Response(JSON.stringify({ result: [{ name: 'readme.txt', size: 10 }] }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/não encontrado no Internet Archive/i)).toBeInTheDocument();
    });
  });

  it('classifies a 5xx response as source-unavailable, not as a missing dataset', async () => {
    mockArchiveFetch(() => Promise.resolve(new Response('server error', { status: 503 })));

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/não encontrado no Internet Archive/i)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tentar verificar novamente/i })).toBeInTheDocument();
  });

  it('classifies a network failure as source-unavailable, not as a missing dataset', async () => {
    mockArchiveFetch(() => Promise.reject(new TypeError('Failed to fetch')));

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/não encontrado no Internet Archive/i)).not.toBeInTheDocument();
  });

  it('does not cache a transient failure as permanent absence, and retry can recover to ready', async () => {
    let calls = 0;
    mockArchiveFetch(() => {
      calls += 1;
      if (calls === 1) {
        return Promise.resolve(new Response('server error', { status: 503 }));
      }
      return Promise.resolve(
        new Response(JSON.stringify({ result: [{ name: 'comunicacoes.parquet', size: 100 }] }), {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      );
    });

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /tentar verificar novamente/i });
    await fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.queryByText(/instabilidade temporária/i)).not.toBeInTheDocument();
    });
    expect(calls).toBe(2);
  });

  it('keeps the tribunal/year selection when the source is transiently unavailable', async () => {
    mockArchiveFetch(() => Promise.resolve(new Response('server error', { status: 503 })));

    render(DuckDBExplorer, { publicBase: '/' });
    await selectTribunalAndYear();

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });

    expect((screen.getByLabelText('Tribunal') as HTMLSelectElement).value).toBe('TJRO');
    expect((screen.getByLabelText('Ano') as HTMLSelectElement).value).toBe(String(CURRENT_YEAR));
  });
});
