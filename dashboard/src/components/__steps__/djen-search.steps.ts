import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  searchDjenComunicacoes,
  clearDjenSearchCache,
  DjenValidationError,
  type DjenComunicacaoQuery,
} from '../../lib/djen';

function mockResponse(
  body: unknown,
  init: { status?: number; headers?: Record<string, string> } = {},
): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: init.headers,
  });
}

// Factory that lazily builds a fresh Response per call because Response bodies
// can only be consumed once.
function mockResponseFactory(
  body: unknown,
  init: { status?: number; headers?: Record<string, string> } = {},
) {
  return () => mockResponse(body, init);
}

function sampleItem(id: number, extra: Record<string, unknown> = {}) {
  return {
    id,
    numeroComunicacao: id,
    siglaTribunal: 'TJSP',
    texto: `sample ${id}`,
    data_disponibilizacao: '2026-04-01',
    ...extra,
  };
}

describe('searchDjenComunicacoes', () => {
  beforeEach(() => {
    clearDjenSearchCache();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    clearDjenSearchCache();
  });

  it('builds the query string correctly from a filled query object', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({ items: [sampleItem(1)], count: 1 }, {
        headers: { 'x-ratelimit-limit': '30', 'x-ratelimit-remaining': '29' },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const query: DjenComunicacaoQuery = {
      siglaTribunal: 'TJSP',
      texto: 'contrato',
      itensPorPagina: 30,
      pagina: 1,
    };

    await searchDjenComunicacoes(query);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const urlCalled = fetchMock.mock.calls[0][0] as string;
    expect(urlCalled).toContain('comunicaapi.pje.jus.br/api/v1/comunicacao?');
    expect(urlCalled).toContain('siglaTribunal=TJSP');
    expect(urlCalled).toContain('texto=contrato');
    expect(urlCalled).toContain('itensPorPagina=30');
    expect(urlCalled).toContain('pagina=1');
  });

  it('throws DjenValidationError when no identity param and itensPorPagina > 5', async () => {
    const fetchMock = vi.fn();
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      searchDjenComunicacoes({ itensPorPagina: 30 } as DjenComunicacaoQuery),
    ).rejects.toBeInstanceOf(DjenValidationError);

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('allows small-page search (itensPorPagina <= 5) without identity param', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({ items: [sampleItem(1)], count: 1 }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await searchDjenComunicacoes({ itensPorPagina: 5 } as DjenComunicacaoQuery);

    expect(result.items).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('parses x-ratelimit-* headers into rateLimit', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({ items: [sampleItem(1)], count: 1 }, {
        headers: { 'x-ratelimit-limit': '30', 'x-ratelimit-remaining': '7' },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });

    expect(result.rateLimit.limit).toBe(30);
    expect(result.rateLimit.remaining).toBe(7);
  });

  it('throws DjenRateLimitError on HTTP 429 without trying the proxy', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({ message: 'Too Many Requests' }, {
        status: 429,
        headers: { 'retry-after': '90' },
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      searchDjenComunicacoes({ siglaTribunal: 'TJSP' }),
    ).rejects.toMatchObject({ name: 'DjenRateLimitError', retryAfterSec: 90 });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('falls back to proxy on public network failure and sets usedFallback', async () => {
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => Promise.reject(new Error('Network error')))
      .mockImplementationOnce(() =>
        Promise.resolve(
          mockResponse({ items: [sampleItem(1)], count: 1 }),
        ),
      );
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });

    expect(result.usedFallback).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondUrl = fetchMock.mock.calls[1][0] as string;
    expect(secondUrl).toContain('djen-proxy-mhgmawcn3a-rj.a.run.app');
  });

  it('caches identical consecutive queries (second call does not hit fetch)', async () => {
    const factory = mockResponseFactory({ items: [sampleItem(1)], count: 1 });
    const fetchMock = vi.fn().mockImplementation(async () => factory());
    global.fetch = fetchMock as unknown as typeof fetch;

    await searchDjenComunicacoes({ siglaTribunal: 'TJSP', texto: 'abc' });
    await searchDjenComunicacoes({ siglaTribunal: 'TJSP', texto: 'abc' });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('bypasses cache when bypassCache: true', async () => {
    const factory = mockResponseFactory({ items: [sampleItem(1)], count: 1 });
    const fetchMock = vi.fn().mockImplementation(async () => factory());
    global.fetch = fetchMock as unknown as typeof fetch;

    await searchDjenComunicacoes({ siglaTribunal: 'TJSP', texto: 'abc' });
    await searchDjenComunicacoes(
      { siglaTribunal: 'TJSP', texto: 'abc' },
      { bypassCache: true },
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('cache TTL expires and refetches', async () => {
    vi.useFakeTimers();
    try {
      const factory = mockResponseFactory({ items: [sampleItem(1)], count: 1 });
      const fetchMock = vi.fn().mockImplementation(async () => factory());
      global.fetch = fetchMock as unknown as typeof fetch;

      await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });
      vi.advanceTimersByTime(61_000);
      await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });

      expect(fetchMock).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it('clearDjenSearchCache() drops all entries', async () => {
    const factory = mockResponseFactory({ items: [sampleItem(1)], count: 1 });
    const fetchMock = vi.fn().mockImplementation(async () => factory());
    global.fetch = fetchMock as unknown as typeof fetch;

    await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });
    clearDjenSearchCache();
    await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('AbortSignal aborts the in-flight fetch and does not populate cache', async () => {
    const fetchMock = vi.fn().mockImplementation(
      (_url: string, init: RequestInit | undefined) =>
        new Promise((_resolve, reject) => {
          const signal = init?.signal;
          if (signal) {
            signal.addEventListener('abort', () => {
              const err = new Error('aborted');
              err.name = 'AbortError';
              reject(err);
            });
          }
        }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const controller = new AbortController();
    const promise = searchDjenComunicacoes(
      { siglaTribunal: 'TJSP' },
      { signal: controller.signal },
    );
    controller.abort();

    await expect(promise).rejects.toMatchObject({ name: 'AbortError' });

    // Follow-up call must hit fetch again because the aborted call did not cache.
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [sampleItem(1)], count: 1 }));
    await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
