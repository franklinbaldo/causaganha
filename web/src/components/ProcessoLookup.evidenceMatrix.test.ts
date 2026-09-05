import { fireEvent, render, waitFor } from '@testing-library/svelte';
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

function foundProcess(overrides = {}) {
  return {
    encontrado: true,
    nrProcesso: CNJ,
    nrProcessoMascara: '0000001-02.2024.8.22.0001',
    fontes: ['djen'],
    djen: { present: true, primeiraPub: '2024-01-01', ultimaPub: '2024-02-01', nPublicacoes: 3, tribunais: ['TJRO'] },
    juris: { present: false, nDocumentos: 0, tipos: [], dataJulgamento: null, orgao: null, relator: null, classe: null, url: null },
    stj: { present: false, id: null, classe: null, relator: null, tema: null, tese: null, ementa: null, dataDecisao: null, dataPublicacao: null },
    datajud: { present: false, classeOficial: null, assuntos: null, orgaoJulgador: null, grau: null, dataAjuizamento: null, ultimaAtualizacao: null },
    jurisUrls: [],
    stjUrls: [],
    cobertura: [],
    datasetGeradoEm: '2026-08-20T10:00:00Z',
    avisos: [],
    ...overrides,
  };
}

beforeEach(() => {
  window.history.replaceState(null, '', '/causaganha/processo');
  localStorage.clear();
  vi.mocked(getDuckDB).mockResolvedValue({ conn: {} } as never);
});

async function submit(component: ReturnType<typeof render>) {
  const input = (await waitFor(() => component.getByLabelText(/Número do processo/i))) as HTMLInputElement;
  await fireEvent.input(input, { target: { value: CNJ } });
  await fireEvent.click(component.getByText('Buscar'));
}

describe('ProcessoLookup — evidence-summary strip (#1130)', () => {
  it('renders the evidence matrix after the main result, before avisos/detail sections', async () => {
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    vi.mocked(processoCnj.carregarDocumentos).mockResolvedValue({ items: [], hasMore: false });
    const component = render(ProcessoLookup);

    await submit(component);
    await waitFor(() => component.getByText('Resumo de evidências por fonte'));

    const container = component.container;
    const snapshotHeading = container.querySelector('#snapshot-title');
    const evidenciasHeading = container.querySelector('#evidencias-title');
    const fontesHeading = container.querySelector('#fontes-title');
    expect(snapshotHeading).toBeTruthy();
    expect(evidenciasHeading).toBeTruthy();
    expect(fontesHeading).toBeTruthy();

    const position = snapshotHeading!.compareDocumentPosition(evidenciasHeading!);
    expect(position & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const positionBeforeFontes = evidenciasHeading!.compareDocumentPosition(fontesHeading!);
    expect(positionBeforeFontes & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('reflects an indisponível source (recorded in avisos) distinctly from an ausente one', async () => {
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(
      foundProcess({ avisos: ["Fonte 'stj' indisponível para este processo: 404"] }) as never,
    );
    vi.mocked(processoCnj.carregarDocumentos).mockResolvedValue({ items: [], hasMore: false });
    const component = render(ProcessoLookup);

    await submit(component);
    await waitFor(() => component.getByText('Resumo de evidências por fonte'));

    expect(component.getByText('Indisponível')).toBeTruthy();
    expect(component.getAllByText('Sem registro').length).toBeGreaterThan(0);
  });
});
