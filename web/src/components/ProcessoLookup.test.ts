import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProcessoLookup from './ProcessoLookup.svelte';
import { getDuckDB } from '../lib/duckdbSingleton';

vi.mock('../lib/duckdbSingleton', () => ({
  getDuckDB: vi.fn(),
}));

beforeEach(() => {
  // Each test mounts its own component instance, but jsdom's window.location
  // persists across tests in this file — without resetting it, a ?cnj= left
  // by history.replaceState() in a previous test would auto-trigger a search
  // on the next test's mount (the component's own, intentional, feature).
  window.history.replaceState(null, '', window.location.pathname);
});

const CNJ_A = '00000010220248220001';
const CNJ_B = '00000020320248220002';

interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
}

function makeDeferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function arrowResult(rows: Record<string, unknown>[]) {
  return { toArray: () => rows.map((r) => ({ toJSON: () => r })) };
}

function processoRow(nrProcesso: string): Record<string, unknown> {
  return {
    nr_processo: nrProcesso,
    nr_processo_mascara: nrProcesso,
    n_fontes: 1,
    fontes: ['djen'],
    djen_primeira_pub: null,
    djen_ultima_pub: null,
    djen_n_publicacoes: null,
    djen_tribunais: [],
    juris_n_documentos: null,
    juris_tipos: [],
    juris_data_julgamento: null,
    juris_orgao: null,
    juris_relator: null,
    juris_classe: null,
    juris_url: null,
    stj_id: null,
    stj_classe: null,
    stj_relator: null,
    stj_tema: null,
    stj_tese: null,
    stj_ementa: null,
    stj_data_decisao: null,
    stj_data_publicacao: null,
    classe_oficial: null,
    assuntos: null,
    orgao_julgador: null,
    grau: null,
    data_ajuizamento: null,
    ultima_atualizacao: null,
    tem_datajud: false,
    updated_at: '2026-07-12T00:00:00Z',
  };
}

function documentoRow(nrProcesso: string, resumo: string): Record<string, unknown> {
  return {
    nr_processo: nrProcesso,
    fonte: 'juris',
    id_documento: `${nrProcesso}-doc`,
    tipo: 'ACÓRDÃO',
    data: '2024-01-15',
    url: null,
    resumo,
  };
}

/** A fake conn whose prepare()/query() resolutions are controlled per-CNJ by the test. */
function makeControllableConn() {
  const processoDeferreds = new Map<string, Deferred<unknown>>();
  const documentosDeferreds = new Map<string, Deferred<unknown>>();

  const conn = {
    prepare: vi.fn(async (sql: string) => {
      const isDocumentos = sql.includes('processo_documentos');
      return {
        query: vi.fn((...params: unknown[]) => {
          const digits = String(params[0]);
          const map = isDocumentos ? documentosDeferreds : processoDeferreds;
          const deferred = makeDeferred();
          map.set(digits, deferred);
          return deferred.promise;
        }),
        close: vi.fn(async () => {}),
      };
    }),
  };

  return { conn, processoDeferreds, documentosDeferreds };
}

describe('ProcessoLookup — race between two searches', () => {
  it('discards a stale documentos response from search A once search B has already landed', async () => {
    const { conn, processoDeferreds, documentosDeferreds } = makeControllableConn();
    vi.mocked(getDuckDB).mockResolvedValue({ conn } as never);

    const { getByLabelText, getByText, queryByText } = render(ProcessoLookup);

    const input = (await waitFor(() => getByLabelText(/Número do processo/i))) as HTMLInputElement;

    // Search A: submit, then let its processo query resolve (found, moves
    // past the "querying" state so the submit button re-enables) while its
    // documentos query is still pending.
    await fireEvent.input(input, { target: { value: CNJ_A } });
    await fireEvent.click(getByText('Buscar'));
    await waitFor(() => expect(processoDeferreds.has(CNJ_A)).toBe(true));

    processoDeferreds.get(CNJ_A)!.resolve(arrowResult([processoRow(CNJ_A)]));
    await waitFor(() => expect(documentosDeferreds.has(CNJ_A)).toBe(true));

    // The record for A is showing, and the button is enabled again — this is
    // exactly the window where the user can fire a second search before A's
    // documents arrive.
    await waitFor(() => expect(getByText(CNJ_A, { exact: false })).toBeTruthy());

    // Search B: submit while A's documentos query is still in flight.
    await fireEvent.input(input, { target: { value: CNJ_B } });
    await fireEvent.click(getByText('Buscar'));
    await waitFor(() => expect(processoDeferreds.has(CNJ_B)).toBe(true));

    processoDeferreds.get(CNJ_B)!.resolve(arrowResult([processoRow(CNJ_B)]));
    await waitFor(() => expect(documentosDeferreds.has(CNJ_B)).toBe(true));
    documentosDeferreds.get(CNJ_B)!.resolve(arrowResult([documentoRow(CNJ_B, 'DOC-B-UNICO')]));

    await waitFor(() => expect(getByText('DOC-B-UNICO')).toBeTruthy());

    // A's documentos response finally arrives, late — it must be discarded,
    // not overwrite B's already-displayed documents.
    documentosDeferreds.get(CNJ_A)!.resolve(arrowResult([documentoRow(CNJ_A, 'DOC-A-UNICO')]));
    await new Promise((r) => setTimeout(r, 0));

    expect(getByText(CNJ_B, { exact: false })).toBeTruthy();
    expect(getByText('DOC-B-UNICO')).toBeTruthy();
    expect(queryByText('DOC-A-UNICO')).toBeNull();
    expect(queryByText(CNJ_A, { exact: false })).toBeNull();
  });

  it('never surfaces a stale processo response from search A once search B has already started', async () => {
    const { conn, processoDeferreds } = makeControllableConn();
    vi.mocked(getDuckDB).mockResolvedValue({ conn } as never);

    const { getByLabelText, getByText, queryByText } = render(ProcessoLookup);
    const input = (await waitFor(() => getByLabelText(/Número do processo/i))) as HTMLInputElement;

    await fireEvent.input(input, { target: { value: CNJ_A } });
    await fireEvent.click(getByText('Buscar'));
    await waitFor(() => expect(processoDeferreds.has(CNJ_A)).toBe(true));

    // B starts (via form submit, bypassing the disabled Buscar button while
    // A is still "querying") before A's own processo query resolves.
    await fireEvent.input(input, { target: { value: CNJ_B } });
    const form = input.closest('form')!;
    await fireEvent.submit(form);
    await waitFor(() => expect(processoDeferreds.has(CNJ_B)).toBe(true));

    // A resolves late — must be discarded entirely (never reaches 'found',
    // never issues its own documentos query).
    processoDeferreds.get(CNJ_A)!.resolve(arrowResult([processoRow(CNJ_A)]));
    await new Promise((r) => setTimeout(r, 0));

    expect(queryByText(CNJ_A, { exact: false })).toBeNull();
  });
});
