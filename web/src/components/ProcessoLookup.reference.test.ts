import { fireEvent, render, waitFor, type RenderResult } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProcessoLookup from './ProcessoLookup.svelte';
import { getDuckDB } from '../lib/duckdbSingleton';
import * as processoCnj from '../lib/processoCnj';

vi.mock('../lib/duckdbSingleton', () => ({ getDuckDB: vi.fn() }));
vi.mock('../lib/processoCnj', async () => {
  const actual = await vi.importActual<typeof import('../lib/processoCnj')>('../lib/processoCnj');
  return {
    ...actual,
    buscarProcesso: vi.fn(),
    carregarDocumentos: vi.fn(),
  };
});

const CNJ = '00000010220248220001';

function foundProcess() {
  return {
    encontrado: true,
    nrProcesso: CNJ,
    nrProcessoMascara: '0000001-02.2024.8.22.0001',
    fontes: ['djen', 'juris'],
    djen: { present: true, primeiraPub: '2024-01-01', ultimaPub: '2024-02-01', nPublicacoes: 3, tribunais: ['TJRO'] },
    juris: { present: true, nDocumentos: 1, tipos: ['Acórdão'], dataJulgamento: '2024-01-15', orgao: '1ª Câmara', relator: null, classe: null, url: null },
    stj: { present: false, id: null, classe: null, relator: null, tema: null, tese: null, ementa: null, dataDecisao: null, dataPublicacao: null },
    datajud: { present: false, classeOficial: null, assuntos: null, orgaoJulgador: null, grau: null, dataAjuizamento: null, ultimaAtualizacao: null },
    jurisUrls: ['https://ia.example/juris.parquet'],
    stjUrls: [],
    cobertura: [],
    datasetGeradoEm: '2026-08-20T10:00:00Z',
    avisos: [],
  };
}

beforeEach(() => {
  window.history.replaceState(null, '', '/causaganha/processo');
  localStorage.clear();
  vi.mocked(getDuckDB).mockResolvedValue({ conn: {} } as never);
});

async function submit(component: RenderResult<typeof ProcessoLookup>) {
  const input = (await waitFor(() => component.getByLabelText(/Número do processo/i))) as HTMLInputElement;
  await fireEvent.input(input, { target: { value: CNJ } });
  await fireEvent.click(component.getByText('Buscar'));
}

describe('ProcessoLookup — copy reference (#1135)', () => {
  it('copies a plain-text dossier reference distinct from the plain permalink', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    vi.mocked(processoCnj.carregarDocumentos).mockResolvedValue({ items: [], hasMore: false });
    const component = render(ProcessoLookup);

    await submit(component);
    await fireEvent.click(await waitFor(() => component.getByText('Copiar referência')));

    expect(writeText).toHaveBeenCalledTimes(1);
    const text = writeText.mock.calls[0][0] as string;
    expect(text).toContain('0000001-02.2024.8.22.0001');
    expect(text).toContain('DJEN');
    expect(text).toContain('2026-08-20T10:00:00Z');
    expect(text).toContain('indice_processual.parquet');
    expect(text).toContain(window.location.origin);
    await waitFor(() => expect(component.getByText('Referência copiada')).toBeTruthy());
  });

  it('offers a per-document reference only for documents that carry a public origin URL', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    vi.mocked(processoCnj.carregarDocumentos).mockResolvedValue({
      items: [
        {
          fonte: 'juris',
          idDocumento: 'juris-1',
          tipo: 'Acórdão',
          data: '2024-01-15',
          url: 'https://tjro.jus.br/juris/acordao/1',
          resumo: null,
        },
        {
          fonte: 'juris',
          idDocumento: 'juris-2',
          tipo: 'Sentença',
          data: null,
          url: null,
          resumo: null,
        },
      ],
      hasMore: false,
    });
    const component = render(ProcessoLookup);

    await submit(component);
    await waitFor(() => component.getByText('Acórdão'));

    const referenceButtons = component.getAllByText('Copiar referência');
    // One for the dossier header + exactly one for the document that has a URL.
    expect(referenceButtons).toHaveLength(2);

    await fireEvent.click(referenceButtons[1]);
    const text = writeText.mock.calls[0][0] as string;
    expect(text).toContain('Acórdão');
    expect(text).toContain('https://tjro.jus.br/juris/acordao/1');
    expect(text).toContain('2024-01-15');
  });
});
