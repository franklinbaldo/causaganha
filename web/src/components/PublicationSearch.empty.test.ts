import { cleanup, fireEvent, screen, waitFor } from '@testing-library/svelte/pure';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PublicationSearchRaw from './PublicationSearch.svelte';
import { render } from './__steps__/shared';
import { clearDjenSearchCache } from '../lib/djen';

const PublicationSearch = PublicationSearchRaw as unknown as Parameters<typeof render>[0];

function emptyResponse() {
  return new Response(JSON.stringify({ items: [], count: 0 }), {
    status: 200,
    headers: {
      'content-type': 'application/json',
      'x-ratelimit-limit': '30',
      'x-ratelimit-remaining': '29',
    },
  });
}

describe('PublicationSearch — actionable empty state', () => {
  beforeEach(() => {
    cleanup();
    clearDjenSearchCache();
    vi.restoreAllMocks();
    window.history.replaceState({}, '', '/publicacoes');
    global.fetch = vi.fn().mockResolvedValue(emptyResponse()) as unknown as typeof fetch;
  });

  afterEach(() => {
    cleanup();
    clearDjenSearchCache();
  });

  it('qualifies zero results and offers filter review plus tribunal coverage', async () => {
    render(PublicationSearch);

    await fireEvent.click(screen.getByRole('button', { name: /Filtros avançados/ }));
    await fireEvent.change(screen.getByLabelText('Tribunal'), { target: { value: 'TJSP' } });
    await fireEvent.click(screen.getByRole('button', { name: /Ocultar filtros/ }));

    const input = screen.getByLabelText('Buscar publicações') as HTMLInputElement;
    await fireEvent.input(input, { target: { value: 'contrato' } });
    await fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(screen.getByText('Nenhum resultado nesta consulta.')).toBeTruthy();
    });
    expect(screen.getByText(/Não prova que a publicação não exista/i)).toBeTruthy();
    expect(screen.queryByLabelText('Tribunal')).toBeNull();

    const coverage = screen.getByRole('button', { name: 'Ver cobertura de TJSP' });
    expect(coverage.getAttribute('href')).toBe('/publicacoes/tjsp');
    expect(screen.getByRole('button', { name: 'Consultar arquivo histórico' })).toBeTruthy();

    await fireEvent.click(screen.getByRole('button', { name: 'Revisar filtros' }));
    expect(screen.getByLabelText('Tribunal')).toBeTruthy();
  });
});
