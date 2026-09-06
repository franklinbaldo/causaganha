import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getDuckDB } from '../lib/duckdbSingleton';
import DuckDBExplorer from './DuckDBExplorer.svelte';

vi.mock('../lib/duckdbSingleton', () => ({ getDuckDB: vi.fn() }));

const START_DATES = { TJRO: '2024-01-01' };
const CURRENT_YEAR = new Date().getUTCFullYear();
const ITEM_ID = `djen-tjro-${CURRENT_YEAR}`;

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

function mockReadyArchiveFetch() {
  const fetchMock = vi.fn((input: string) => {
    const url = String(input);
    if (url.endsWith('tribunal_start_dates.json')) {
      return Promise.resolve(
        new Response(JSON.stringify(START_DATES), { status: 200, headers: { 'content-type': 'application/json' } }),
      );
    }
    return Promise.resolve(
      new Response(JSON.stringify({ result: [{ name: 'comunicacoes.parquet', size: 100 }] }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

function fakeQueryResult(rows: Record<string, unknown>[] = [{ total: 1 }]) {
  const columns = rows.length > 0 ? Object.keys(rows[0]) : [];
  return {
    schema: { fields: columns.map((name) => ({ name })) },
    toArray: () => rows.map((row) => ({ toJSON: () => row })),
    numRows: rows.length,
  };
}

async function runQueryWith(queryImpl: (sql: string) => Promise<unknown>) {
  const conn = { query: vi.fn(queryImpl) };
  vi.mocked(getDuckDB).mockResolvedValue({ db: {}, conn } as never);
  mockReadyArchiveFetch();

  render(DuckDBExplorer, { publicBase: '/' });
  await selectTribunalAndYear();

  await waitFor(() => {
    expect(screen.queryByText(/verificando dataset/i)).not.toBeInTheDocument();
  });

  const textarea = screen.getByLabelText('Editor SQL') as HTMLTextAreaElement;
  await fireEvent.input(textarea, { target: { value: 'SELECT 1' } });

  const runButton = screen.getByRole('button', { name: /executar/i });
  await waitFor(() => expect(runButton).not.toBeDisabled());
  await fireEvent.click(runButton);

  return { conn, runButton, textarea };
}

beforeEach(() => {
  vi.mocked(getDuckDB).mockResolvedValue({ db: {}, conn: {} } as never);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('DuckDBExplorer runQuery() error classification', () => {
  it('does not classify a transient 5xx error during query execution as a missing dataset', async () => {
    await runQueryWith(() =>
      Promise.reject(
        new Error(
          `IO Error: HTTP GET error on 'https://archive.org/download/${ITEM_ID}/comunicacoes.parquet': status 503`,
        ),
      ),
    );

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/não encontrado no Internet Archive/i)).not.toBeInTheDocument();
  });

  it('does not classify a network failure during query execution as a missing dataset', async () => {
    await runQueryWith(() => Promise.reject(new TypeError('Failed to fetch')));

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });
    expect(screen.queryByText(/não encontrado no Internet Archive/i)).not.toBeInTheDocument();
  });

  it('classifies an unambiguous remote-file-not-found error as a missing dataset without hiding the original message', async () => {
    const originalMessage = `IO Error: HTTP GET error on 'https://archive.org/download/${ITEM_ID}/comunicacoes.parquet': status 404 (Not Found)`;
    await runQueryWith(() => Promise.reject(new Error(originalMessage)));

    await waitFor(() => {
      expect(screen.getByText(/não encontrado no Internet Archive/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('alert').textContent).toContain(originalMessage);
  });

  it('shows a local SQL error unrelated to the source as-is, undecorated', async () => {
    const originalMessage = 'Parser Error: syntax error at or near "SELET"';
    await runQueryWith(() => Promise.reject(new Error(originalMessage)));

    await waitFor(() => {
      expect(screen.getByText(originalMessage)).toBeInTheDocument();
    });
    expect(screen.queryByText(/instabilidade temporária/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/não encontrado no Internet Archive/i)).not.toBeInTheDocument();
  });

  it('preserves tribunal/year selection and typed SQL after a transient query error', async () => {
    const { textarea } = await runQueryWith(() => Promise.reject(new Error('HTTP Error: 500 Internal Server Error')));

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });

    expect((screen.getByLabelText('Tribunal') as HTMLSelectElement).value).toBe('TJRO');
    expect((screen.getByLabelText('Ano') as HTMLSelectElement).value).toBe(String(CURRENT_YEAR));
    expect(textarea.value).toBe('SELECT 1');
  });

  it('allows retrying execution after a transient query error and succeeding, without a page reload', async () => {
    let calls = 0;
    const { runButton } = await runQueryWith(() => {
      calls += 1;
      if (calls === 1) {
        return Promise.reject(new Error('HTTP Error: 502 Bad Gateway'));
      }
      return Promise.resolve(fakeQueryResult([{ total: 1 }]));
    });

    await waitFor(() => {
      expect(screen.getByText(/instabilidade temporária/i)).toBeInTheDocument();
    });

    await fireEvent.click(runButton);

    await waitFor(() => {
      expect(screen.queryByText(/instabilidade temporária/i)).not.toBeInTheDocument();
    });
    expect(calls).toBe(2);
  });
});
