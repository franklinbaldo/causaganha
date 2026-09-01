import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProcessoLookup from './ProcessoLookup.svelte';
import { getDuckDB } from '../lib/duckdbSingleton';
import * as processoCnj from '../lib/processoCnj';
import { SAVED_CONSULTATIONS_STORAGE_KEY, parseSavedConsultations } from '../lib/savedConsultations';

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
    fontes: ['djen', 'datajud'],
    djen: {
      present: true,
      primeiraPub: '2024-01-01',
      ultimaPub: '2024-02-01',
      nPublicacoes: 3,
      tribunais: ['TJRO'],
    },
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
      present: true,
      classeOficial: 'Mandado de Segurança',
      assuntos: 'Direito Administrativo',
      orgaoJulgador: '1ª Câmara',
      grau: 'G2',
      dataAjuizamento: '2024-01-01',
      ultimaAtualizacao: '2024-02-02',
    },
    jurisUrls: [],
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
  vi.mocked(processoCnj.carregarDocumentos).mockResolvedValue({ items: [], hasMore: false });
});

async function submit(component: ReturnType<typeof render>) {
  const input = (await waitFor(() => component.getByLabelText(/Número do processo/i))) as HTMLInputElement;
  await fireEvent.input(input, { target: { value: CNJ } });
  await fireEvent.click(component.getByText('Buscar'));
}

describe('ProcessoLookup — next actions', () => {
  it('links the dossier to the DJEN search and does not invent a documents jump', async () => {
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    const component = render(ProcessoLookup);

    await submit(component);

    const link = await waitFor(() => component.getByText('Ver publicações DJEN'));
    expect(link.getAttribute('href')).toContain(`numeroProcesso=${CNJ}`);
    expect(component.queryByText('Ir para documentos')).toBeNull();
    expect(component.container.textContent).toContain('Estes valores descrevem o acervo publicado do CausaGanha');
  });

  it('saves the current CNJ locally without a network-backed account', async () => {
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    const component = render(ProcessoLookup);

    await submit(component);
    await fireEvent.click(await waitFor(() => component.getByText('Salvar em Minhas consultas')));

    const saved = parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY));
    expect(saved).toHaveLength(1);
    expect(saved[0].type).toBe('processo');
    if (saved[0].type === 'processo') expect(saved[0].cnj).toBe(CNJ);
    expect(component.getByText('Salvo em Minhas consultas')).toBeTruthy();
  });

  it('offers the DJEN route when the reconciled snapshot has no process record', async () => {
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue({ encontrado: false, legado: false } as never);
    const component = render(ProcessoLookup);

    await submit(component);

    const link = await waitFor(() => component.getByText('Pesquisar este CNJ no DJEN'));
    expect(link.getAttribute('href')).toContain(`numeroProcesso=${CNJ}`);
    expect(component.container.textContent).toContain('não que o processo não existe');
  });

  it('keeps source failure distinct from absence and offers an independent route', async () => {
    vi.mocked(processoCnj.buscarProcesso).mockRejectedValue(new Error('archive offline'));
    const component = render(ProcessoLookup);

    await submit(component);

    await waitFor(() => expect(component.container.textContent).toContain('Fonte indisponível'));
    expect(component.container.textContent).toContain('O erro não significa ausência do processo');
    const link = component.getByText('Pesquisar este CNJ no DJEN');
    expect(link.getAttribute('href')).toContain(`numeroProcesso=${CNJ}`);
  });

  // Issue #907: a "não encontrado" state must also expose the snapshot's
  // freshness — buscarProcesso() already returns datasetGeradoEm on the
  // not-found result (processoCnj.ts), but nothing rendered it, so an old
  // snapshot's absence looked identical to a fresh one's.
  it('warns that the snapshot may be stale when the CNJ is absent from an old dataset', async () => {
    const staleTimestamp = new Date(Date.now() - 60 * 60 * 60 * 1000).toISOString(); // 60h ago
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue({
      encontrado: false,
      legado: false,
      datasetGeradoEm: staleTimestamp,
    } as never);
    const component = render(ProcessoLookup);

    await submit(component);

    await waitFor(() => expect(component.container.textContent).toContain('Pesquisar este CNJ no DJEN'));
    expect(component.container.textContent).toContain('pode estar desatualizado');
  });

  it('shows the dataset generation timestamp without a staleness warning when it is fresh', async () => {
    const freshTimestamp = new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(); // 1h ago
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue({
      encontrado: false,
      legado: false,
      datasetGeradoEm: freshTimestamp,
    } as never);
    const component = render(ProcessoLookup);

    await submit(component);

    await waitFor(() => expect(component.container.textContent).toContain('dataset gerado em'));
    expect(component.container.textContent).not.toContain('pode estar desatualizado');
  });
});
