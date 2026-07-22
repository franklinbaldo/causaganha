import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProcessoLookup from './ProcessoLookup.svelte';
import { getDuckDB } from '../lib/duckdbSingleton';
import * as processoCnj from '../lib/processoCnj';

vi.mock('../lib/duckdbSingleton', () => ({
  getDuckDB: vi.fn(),
}));

// buscarProcesso/carregarDocumentos' own SQL-building and row-mapping logic
// is unit-tested in processoCnj.test.ts against a fake DuckDB connection —
// here only the component's orchestration (async race handling, rendering)
// is under test, so those two functions are mocked at their natural seam;
// everything else (formatCnj, fontesPresenca, etc.) stays real.
vi.mock('../lib/processoCnj', async () => {
  const actual = await vi.importActual<typeof import('../lib/processoCnj')>('../lib/processoCnj');
  return {
    ...actual,
    buscarProcesso: vi.fn(),
    carregarDocumentos: vi.fn(),
  };
});

beforeEach(() => {
  // Each test mounts its own component instance, but jsdom's window.location
  // persists across tests in this file — without resetting it, a ?cnj= left
  // by history.replaceState() in a previous test would auto-trigger a search
  // on the next test's mount (the component's own, intentional, feature).
  window.history.replaceState(null, '', window.location.pathname);
  vi.mocked(getDuckDB).mockResolvedValue({ conn: {} } as never);
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

function processoResultado(nrProcesso: string, overrides: Record<string, unknown> = {}) {
  return {
    encontrado: true,
    nrProcesso,
    nrProcessoMascara: nrProcesso,
    fontes: ['djen'],
    djen: { present: true, primeiraPub: null, ultimaPub: null, nPublicacoes: null, tribunais: [] },
    juris: {
      present: false,
      nDocumentos: null,
      tipos: [],
      dataJulgamento: null,
      orgao: null,
      relator: null,
      classe: null,
      url: null,
    },
    stj: {
      present: false,
      id: null,
      classe: null,
      relator: null,
      tema: null,
      tese: null,
      ementa: null,
      dataDecisao: null,
      dataPublicacao: null,
    },
    datajud: {
      present: false,
      classeOficial: null,
      assuntos: null,
      orgaoJulgador: null,
      grau: null,
      dataAjuizamento: null,
      ultimaAtualizacao: null,
    },
    jurisUrls: [],
    stjUrls: [],
    cobertura: [],
    datasetGeradoEm: null,
    avisos: [],
    ...overrides,
  };
}

function documentoRow(nrProcesso: string, resumo: string) {
  return { fonte: 'juris', idDocumento: `${nrProcesso}-doc`, tipo: 'ACÓRDÃO', data: '2024-01-15', url: null, resumo };
}

/** Controls buscarProcesso()/carregarDocumentos() resolution per-CNJ, mirroring the old per-query control. */
function makeControllable() {
  const processoDeferreds = new Map<string, Deferred<unknown>>();
  const documentosDeferreds = new Map<string, Deferred<unknown>>();

  vi.mocked(processoCnj.buscarProcesso).mockImplementation((_conn: unknown, digits: string) => {
    const deferred = makeDeferred();
    processoDeferreds.set(digits, deferred);
    return deferred.promise as ReturnType<typeof processoCnj.buscarProcesso>;
  });

  vi.mocked(processoCnj.carregarDocumentos).mockImplementation((_conn: unknown, _jurisUrls, _stjUrls, digits: string) => {
    const deferred = makeDeferred();
    documentosDeferreds.set(digits, deferred);
    return deferred.promise as ReturnType<typeof processoCnj.carregarDocumentos>;
  });

  return { processoDeferreds, documentosDeferreds };
}

describe('ProcessoLookup — race between two searches', () => {
  it('discards a stale documentos response from search A once search B has already landed', async () => {
    const { processoDeferreds, documentosDeferreds } = makeControllable();

    const { getByLabelText, getByText, queryByText } = render(ProcessoLookup);

    const input = (await waitFor(() => getByLabelText(/Número do processo/i))) as HTMLInputElement;

    // Search A: submit, then let its processo query resolve (found, moves
    // past the "querying" state so the submit button re-enables) while its
    // documentos query is still pending.
    await fireEvent.input(input, { target: { value: CNJ_A } });
    await fireEvent.click(getByText('Buscar'));
    await waitFor(() => expect(processoDeferreds.has(CNJ_A)).toBe(true));

    processoDeferreds.get(CNJ_A)!.resolve(processoResultado(CNJ_A));
    await waitFor(() => expect(documentosDeferreds.has(CNJ_A)).toBe(true));

    // The record for A is showing, and the button is enabled again — this is
    // exactly the window where the user can fire a second search before A's
    // documents arrive.
    await waitFor(() => expect(getByText(CNJ_A, { exact: false })).toBeTruthy());

    // Search B: submit while A's documentos query is still in flight.
    await fireEvent.input(input, { target: { value: CNJ_B } });
    await fireEvent.click(getByText('Buscar'));
    await waitFor(() => expect(processoDeferreds.has(CNJ_B)).toBe(true));

    processoDeferreds.get(CNJ_B)!.resolve(processoResultado(CNJ_B));
    await waitFor(() => expect(documentosDeferreds.has(CNJ_B)).toBe(true));
    documentosDeferreds.get(CNJ_B)!.resolve({ items: [documentoRow(CNJ_B, 'DOC-B-UNICO')], hasMore: false });

    await waitFor(() => expect(getByText('DOC-B-UNICO')).toBeTruthy());

    // A's documentos response finally arrives, late — it must be discarded,
    // not overwrite B's already-displayed documents.
    documentosDeferreds.get(CNJ_A)!.resolve({ items: [documentoRow(CNJ_A, 'DOC-A-UNICO')], hasMore: false });
    await new Promise((r) => setTimeout(r, 0));

    expect(getByText(CNJ_B, { exact: false })).toBeTruthy();
    expect(getByText('DOC-B-UNICO')).toBeTruthy();
    expect(queryByText('DOC-A-UNICO')).toBeNull();
    expect(queryByText(CNJ_A, { exact: false })).toBeNull();
  });

  it('never surfaces a stale processo response from search A once search B has already started', async () => {
    const { processoDeferreds } = makeControllable();

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
    processoDeferreds.get(CNJ_A)!.resolve(processoResultado(CNJ_A));
    await new Promise((r) => setTimeout(r, 0));

    expect(queryByText(CNJ_A, { exact: false })).toBeNull();
  });
});

describe('ProcessoLookup — source presence copy (no false completeness score)', () => {
  async function searchAndResolve(
    cnj: string,
    processoOverrides: Record<string, unknown>,
    documentoRows: Record<string, unknown>[],
  ) {
    const { processoDeferreds, documentosDeferreds } = makeControllable();

    const { getByLabelText, getByText, container } = render(ProcessoLookup);
    const input = (await waitFor(() => getByLabelText(/Número do processo/i))) as HTMLInputElement;

    await fireEvent.input(input, { target: { value: cnj } });
    await fireEvent.click(getByText('Buscar'));
    await waitFor(() => expect(processoDeferreds.has(cnj)).toBe(true));
    processoDeferreds.get(cnj)!.resolve(processoResultado(cnj, processoOverrides));
    await waitFor(() => expect(documentosDeferreds.has(cnj)).toBe(true));
    documentosDeferreds.get(cnj)!.resolve({ items: documentoRows, hasMore: false });

    return container;
  }

  it('shows the source count without a percentage when one source is present', async () => {
    const cnj = '00000030420248220003';
    const container = await searchAndResolve(cnj, {}, []);

    await waitFor(() => expect(container.textContent).toContain('Registros encontrados em 1 das 4 fontes consultadas'));
    expect(container.textContent).not.toContain('% de completude');
  });

  it('shows the correct source count when multiple sources are present', async () => {
    const cnj = '00000040520248220004';
    const container = await searchAndResolve(
      cnj,
      {
        fontes: ['djen', 'juris'],
        juris: {
          present: true,
          nDocumentos: 2,
          tipos: ['ACÓRDÃO'],
          dataJulgamento: '2024-01-01',
          orgao: null,
          relator: null,
          classe: null,
          url: null,
        },
      },
      [documentoRow(cnj, 'DOC-MULTI')],
    );

    await waitFor(() => expect(container.textContent).toContain('Registros encontrados em 2 das 4 fontes consultadas'));
  });

  it('labels an absent source as "sem registro", never "ausente"', async () => {
    const cnj = '00000050620248220005';
    const container = await searchAndResolve(cnj, {}, []);

    await waitFor(() => expect(container.textContent).toContain('STJ — sem registro'));
    expect(container.textContent).not.toContain('ausente');
  });

  it('explains an empty documents section without contradicting the DJEN publications shown above', async () => {
    const cnj = '00000060720248220006';
    const container = await searchAndResolve(
      cnj,
      { djen: { present: true, primeiraPub: null, ultimaPub: null, nPublicacoes: 3, tribunais: [] } },
      [],
    );

    await waitFor(() => expect(container.textContent).toContain('Nenhum documento de decisão encontrado no JURIS ou no STJ'));
    expect(container.textContent).not.toContain('sem documentos associados');
  });

  it('shows the same empty-documents message when there are no DJEN publications either', async () => {
    const cnj = '00000070820248220007';
    const container = await searchAndResolve(
      cnj,
      {
        fontes: ['juris'],
        djen: { present: false, primeiraPub: null, ultimaPub: null, nPublicacoes: null, tribunais: [] },
        juris: {
          present: true,
          nDocumentos: 0,
          tipos: [],
          dataJulgamento: null,
          orgao: null,
          relator: null,
          classe: null,
          url: null,
        },
      },
      [],
    );

    await waitFor(() => expect(container.textContent).toContain('Nenhum documento de decisão encontrado no JURIS ou no STJ'));
  });
});
