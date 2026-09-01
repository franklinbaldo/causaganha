import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { QueryClient } from '@tanstack/svelte-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PublicationSearchRaw from './PublicationSearch.svelte';
import * as djen from '../lib/djen';

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
    siglaTribunal: 'TJSP',
    texto: `Exemplo de publicação ${id}`,
    data_disponibilizacao: '2026-04-01',
    tipoDocumento: 'Intimação',
    nomeOrgao: 'Vara X',
    destinatarios: [],
    destinatarioadvogados: [],
  };
}

async function searchAndGetResults(itemCount: number, totalCount: number) {
  vi.mocked(djen.searchDjenComunicacoes).mockResolvedValue({
    items: Array.from({ length: itemCount }, (_, i) => samplePublication(i + 1)),
    count: totalCount,
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
  await waitFor(() => expect(component.getByText(`${totalCount} resultado(s)`)).toBeTruthy());
  return component;
}

beforeEach(() => {
  window.history.replaceState({}, '', '/');
  vi.restoreAllMocks();
});

describe('PublicationSearch — copy search link', () => {
  it('copies the current, reproducible search URL to the clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });

    const component = await searchAndGetResults(2, 2);
    await fireEvent.click(component.getByText('Copiar link desta busca'));

    expect(writeText).toHaveBeenCalledWith(window.location.href);
    expect(window.location.href).toContain('texto=contrato');
    await waitFor(() => expect(component.getByText('Link copiado')).toBeTruthy());
  });
});

describe('PublicationSearch — export current page as CSV', () => {
  it('exports only the current page, with the scope explicit in the filename', async () => {
    let capturedParts: string[] | null = null;
    let downloadName: string | null = null;
    const OriginalBlob = globalThis.Blob;
    vi.stubGlobal(
      'Blob',
      class extends OriginalBlob {
        constructor(parts: string[], opts?: BlobPropertyBag) {
          super(parts, opts);
          capturedParts = parts;
        }
      },
    );
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => 'blob:mock-url');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      downloadName = this.download;
    });

    // 2 items on this page out of 45 total across several pages.
    const component = await searchAndGetResults(2, 45);
    await fireEvent.click(component.getByText('Exportar CSV (página atual)'));

    expect(downloadName).toMatch(/pagina-1/);
    expect(downloadName).toMatch(/2-itens/);
    expect(downloadName).not.toMatch(/45/);
    expect(downloadName).toMatch(/\.csv$/);

    expect(capturedParts).not.toBeNull();
    const text = (capturedParts as unknown as string[]).join('');
    expect(text).toContain('Exemplo de publicação 1');
    expect(text).toContain('Exemplo de publicação 2');
    expect(text.toLowerCase()).toContain('página');
    expect(text).toMatch(/itens nesta página: 2/i);
  });
});
