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
    fontes: ['djen'],
    djen: { present: true, primeiraPub: '2024-01-01', ultimaPub: '2024-02-01', nPublicacoes: 3, tribunais: ['TJRO'] },
    juris: { present: false, nDocumentos: null, tipos: [], dataJulgamento: null, orgao: null, relator: null, classe: null, url: null },
    stj: { present: false, id: null, classe: null, relator: null, tema: null, tese: null, ementa: null, dataDecisao: null, dataPublicacao: null },
    datajud: { present: false, classeOficial: null, assuntos: null, orgaoJulgador: null, grau: null, dataAjuizamento: null, ultimaAtualizacao: null },
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

async function submit(component: RenderResult<typeof ProcessoLookup>) {
  const input = (await waitFor(() => component.getByLabelText(/Número do processo/i))) as HTMLInputElement;
  await fireEvent.input(input, { target: { value: CNJ } });
  await fireEvent.click(component.getByText('Buscar'));
}

describe('ProcessoLookup — continue with an agent (#1225)', () => {
  it('copies a task-language agent question containing exactly the consulted CNJ, distinct from the permalink and the reference', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    const component = render(ProcessoLookup);

    await submit(component);
    await fireEvent.click(await waitFor(() => component.getByText('Continuar com um agente')));

    expect(writeText).toHaveBeenCalledTimes(1);
    const question = writeText.mock.calls[0][0] as string;
    expect(question).toContain('0000001-02.2024.8.22.0001');
    expect(question.toLowerCase()).not.toContain('http');
    expect(question).not.toContain(window.location.origin);
    await waitFor(() => expect(component.getByText('Pergunta copiada')).toBeTruthy());

    // Semantically distinct from the other two copy actions on the same dossier.
    await fireEvent.click(component.getByText('Copiar link'));
    const link = writeText.mock.calls[1][0] as string;
    expect(link).not.toBe(question);
    expect(link).toContain(window.location.origin);

    await fireEvent.click(component.getByText('Copiar referência'));
    const reference = writeText.mock.calls[2][0] as string;
    expect(reference).not.toBe(question);
    expect(reference).not.toBe(link);
  });

  it('offers a secondary onboarding link to /agentes and never sends the CNJ to a server on its own', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    const component = render(ProcessoLookup);

    await submit(component);
    await waitFor(() => component.getByText('Continuar com um agente'));

    const agentesLink = component.getByText(/agentes/i, { selector: 'a' });
    expect(agentesLink.getAttribute('href')).toContain('agentes');

    const callsBeforeCopy = vi.mocked(processoCnj.buscarProcesso).mock.calls.length;
    await fireEvent.click(component.getByText('Continuar com um agente'));
    // Copying is a pure clipboard write — it must not trigger another lookup/network call.
    expect(processoCnj.buscarProcesso).toHaveBeenCalledTimes(callsBeforeCopy);
  });

  it('falls back gracefully when the clipboard API is unavailable', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(foundProcess() as never);
    const component = render(ProcessoLookup);

    await submit(component);
    await fireEvent.click(await waitFor(() => component.getByText('Continuar com um agente')));

    expect(component.queryByText('Pergunta copiada')).toBeNull();
    expect(component.getByText('Continuar com um agente')).toBeTruthy();
  });
});
