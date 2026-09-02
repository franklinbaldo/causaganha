import { cleanup, fireEvent, screen, waitFor } from '@testing-library/svelte/pure';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AnnualCoverageMonitorRaw from './AnnualCoverageMonitor.svelte';
import ProcessoLookupRaw from './ProcessoLookup.svelte';
import PublicationSearchRaw from './PublicationSearch.svelte';
import { render } from './__steps__/shared';
import { clearDjenSearchCache } from '../lib/djen';
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

const AnnualCoverageMonitor = AnnualCoverageMonitorRaw as unknown as Parameters<typeof render>[0];
const ProcessoLookup = ProcessoLookupRaw as unknown as Parameters<typeof render>[0];
const PublicationSearch = PublicationSearchRaw as unknown as Parameters<typeof render>[0];
const CNJ = '00000010220248220001';

function response(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

beforeEach(() => {
  cleanup();
  clearDjenSearchCache();
  vi.restoreAllMocks();
  localStorage.clear();
  vi.mocked(getDuckDB).mockResolvedValue({ conn: {} } as never);
  vi.mocked(processoCnj.carregarDocumentos).mockResolvedValue({ items: [], hasMore: false });
});

afterEach(() => {
  cleanup();
  clearDjenSearchCache();
});

describe('empty/error-state contract across public product surfaces (#907)', () => {
  it('keeps invalid CNJ distinct from absence before consulting a source', async () => {
    window.history.replaceState({}, '', '/causaganha/processo?ref=empty-state-contract');
    const component = render(ProcessoLookup);

    const input = (await waitFor(() => component.getByLabelText(/Número do processo/i))) as HTMLInputElement;
    await fireEvent.input(input, { target: { value: '123' } });
    await fireEvent.click(component.getByText('Buscar'));

    expect(await waitFor(() => component.getByText('CNJ inválido'))).toBeTruthy();
    expect(processoCnj.buscarProcesso).not.toHaveBeenCalled();
    expect(component.queryByText(/Processo não localizado neste snapshot/i)).toBeNull();
  });

  it('preserves the CNJ and unrelated URL state when the reconciled snapshot is empty', async () => {
    window.history.replaceState({}, '', '/causaganha/processo?ref=empty-state-contract');
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue({
      encontrado: false,
      legado: false,
      datasetGeradoEm: '2026-08-20T10:00:00Z',
    } as never);
    const component = render(ProcessoLookup);

    const input = (await waitFor(() => component.getByLabelText(/Número do processo/i))) as HTMLInputElement;
    await fireEvent.input(input, { target: { value: CNJ } });
    await fireEvent.click(component.getByText('Buscar'));

    const alternative = await waitFor(() => component.getByText('Pesquisar este CNJ no DJEN'));
    const params = new URLSearchParams(window.location.search);
    expect(params.get('cnj')).toBe(CNJ);
    expect(params.get('ref')).toBe('empty-state-contract');
    expect(alternative.getAttribute('href')).toContain(`numeroProcesso=${CNJ}`);
    expect(component.container.textContent).toContain('não que o processo não existe');
  });

  it('preserves text, tribunal and period when the DJEN source is unavailable', async () => {
    window.history.replaceState({}, '', '/causaganha/publicacoes');
    global.fetch = vi.fn().mockResolvedValue(response(502, { message: 'Bad Gateway' })) as unknown as typeof fetch;
    render(PublicationSearch);

    await fireEvent.click(screen.getByRole('button', { name: /Filtros avançados/ }));
    await fireEvent.change(screen.getByLabelText('Tribunal'), { target: { value: 'TJSP' } });
    await fireEvent.input(screen.getByLabelText('Data início'), { target: { value: '2026-08-01' } });
    await fireEvent.input(screen.getByLabelText('Data fim'), { target: { value: '2026-08-31' } });

    const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'contrato' } });
    await fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => expect(screen.getByText('Não foi possível buscar.')).toBeTruthy(), { timeout: 8000 });

    const params = new URLSearchParams(window.location.search);
    expect(params.get('texto')).toBe('contrato');
    expect(params.get('siglaTribunal')).toBe('TJSP');
    expect(params.get('dataDisponibilizacaoInicio')).toBe('2026-08-01');
    expect(params.get('dataDisponibilizacaoFim')).toBe('2026-08-31');
    expect(screen.queryByText('Nenhum resultado nesta consulta.')).toBeNull();
  }, 10000);

  it('keeps an Internet Archive outage distinct from confirmed coverage absence and exposes retry', async () => {
    window.history.replaceState({}, '', '/causaganha/cobertura');
    global.fetch = vi.fn().mockResolvedValue(response(503, { message: 'Service Unavailable' })) as unknown as typeof fetch;
    render(AnnualCoverageMonitor);

    await waitFor(
      () => expect(screen.getByText('Não foi possível verificar a cobertura.')).toBeTruthy(),
      { timeout: 8000 },
    );

    expect(screen.getByText(/não confirma ausência de arquivos/i)).toBeTruthy();
    expect(screen.queryByRole('table')).toBeNull();
    expect(screen.getByRole('button', { name: 'Tentar novamente' })).toBeTruthy();
  }, 10000);
});
