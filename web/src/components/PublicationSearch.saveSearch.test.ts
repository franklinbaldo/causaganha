import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PublicationSearchRaw from './PublicationSearch.svelte';
import * as djen from '../lib/djen';
import {
  SAVED_CONSULTATIONS_STORAGE_KEY,
  parseSavedConsultations,
} from '../lib/savedConsultations';

// See src/components/__steps__/shared.ts for why this cast is needed:
// Astro's Svelte integration reshapes the component's exported type in a way
// that no longer matches what @testing-library/svelte's render() expects,
// even though the runtime component is unaffected.
const PublicationSearch = PublicationSearchRaw as unknown as Parameters<typeof render>[0];

vi.mock('../lib/queryClient', () => ({
  getQueryClient: () =>
    new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } }),
}));

vi.mock('../lib/djen', async () => {
  const actual = await vi.importActual<typeof import('../lib/djen')>('../lib/djen');
  return { ...actual, searchDjenComunicacoes: vi.fn() };
});

function samplePublication(id: number) {
  return {
    id,
    numeroComunicacao: id,
    siglaTribunal: 'TJRO',
    texto: `Exemplo de publicação ${id}`,
    data_disponibilizacao: '2026-04-01',
    tipoDocumento: 'Intimação',
    nomeOrgao: 'Vara X',
    destinatarios: [],
    destinatarioadvogados: [],
  };
}

async function searchAndGetResults() {
  vi.mocked(djen.searchDjenComunicacoes).mockResolvedValue({
    items: [samplePublication(1)],
    count: 1,
    rateLimit: { limit: null, remaining: null, resetAt: null },
    source: 'djen',
    usedFallback: false,
  });

  const component = render(PublicationSearch);
  const input = (await waitFor(() =>
    component.getByLabelText('Buscar publicações'),
  )) as HTMLInputElement;
  await fireEvent.input(input, { target: { value: 'contrato' } });
  await fireEvent.keyDown(input, { key: 'Enter' });
  await waitFor(() => expect(component.getByText('1 resultado(s)')).toBeTruthy());
  return component;
}

beforeEach(() => {
  window.history.replaceState({}, '', '/');
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('PublicationSearch — save search to Minhas consultas', () => {
  it('saves the current search locally, keyed by its canonical params', async () => {
    const component = await searchAndGetResults();

    await fireEvent.click(component.getByText('Salvar busca'));

    const saved = parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY));
    expect(saved).toHaveLength(1);
    expect(saved[0].type).toBe('busca');
    if (saved[0].type === 'busca') {
      expect(saved[0].params).toContain('texto=contrato');
      expect(saved[0].label).not.toBe('');
    }
    await waitFor(() => expect(component.getByText('Busca salva em Minhas consultas.')).toBeTruthy());
    expect(component.getByText('Remover de Minhas consultas')).toBeTruthy();
  });

  it('toggles: clicking again removes the saved search without a network call', async () => {
    const component = await searchAndGetResults();

    await fireEvent.click(component.getByText('Salvar busca'));
    await waitFor(() => component.getByText('Remover de Minhas consultas'));
    await fireEvent.click(component.getByText('Remover de Minhas consultas'));

    const saved = parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY));
    expect(saved).toHaveLength(0);
    await waitFor(() => expect(component.getByText('Busca removida de Minhas consultas.')).toBeTruthy());
    expect(component.getByText('Salvar busca')).toBeTruthy();
  });
});
