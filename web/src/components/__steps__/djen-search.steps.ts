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

/**
 * `openapi-fetch` calls the underlying fetch with a single `Request` object
 * (not a `string, init` pair), so tests that want to inspect the URL must
 * reach through the Request instance rather than the legacy `init` arg.
 */
function firstRequestUrl(fetchMock: ReturnType<typeof vi.fn>): string {
  const firstCall = fetchMock.mock.calls[0];
  if (!firstCall) return '';
  const input = firstCall[0];
  if (input instanceof Request) return input.url;
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return String(input);
}

function callRequestUrl(
  fetchMock: ReturnType<typeof vi.fn>,
  callIndex: number,
): string {
  const call = fetchMock.mock.calls[callIndex];
  if (!call) return '';
  const input = call[0];
  if (input instanceof Request) return input.url;
  if (typeof input === 'string') return input;
  if (input instanceof URL) return input.toString();
  return String(input);
}

describe('searchDjenComunicacoes', () => {
  beforeEach(() => {
    // Reset the geo-fence state machine between scenarios so the direct-first
    // flow applies to each test. `clearDjenSearchCache()` now just resets the
    // geo-state (library-level caching was removed when TanStack Query took
    // over caching at the component layer).
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
    const urlCalled = firstRequestUrl(fetchMock);
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
    // A geo-block (CORS / DNS / unreachable) surfaces from `fetch` as a
    // TypeError — the only shape `isGeoBlockShape()` in `djenClient.ts`
    // classifies as a reason to try the proxy. Plain `Error` instances are
    // treated as real backend failures and propagate to the caller.
    const fetchMock = vi
      .fn()
      .mockImplementationOnce(() => Promise.reject(new TypeError('Failed to fetch')))
      .mockImplementationOnce(() =>
        Promise.resolve(mockResponse({ items: [sampleItem(1)], count: 1 })),
      );
    global.fetch = fetchMock as unknown as typeof fetch;

    const result = await searchDjenComunicacoes({ siglaTribunal: 'TJSP' });

    expect(result.usedFallback).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    const secondUrl = callRequestUrl(fetchMock, 1);
    expect(secondUrl).toContain('djen-proxy-mhgmawcn3a-rj.a.run.app');
  });

  it('propagates HTTP 5xx without trying the proxy (real backend errors are not masked)', async () => {
    // 5xx is the key bug-fix over the old implementation: previously any
    // failure triggered the proxy retry, which silently masked real public-
    // side backend bugs. The new classifier keeps 5xx as a hard failure.
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({ message: 'Internal Server Error' }, { status: 502 }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(
      searchDjenComunicacoes({ siglaTribunal: 'TJSP' }),
    ).rejects.toMatchObject({ name: 'DjenHttpError', status: 502 });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const urlCalled = firstRequestUrl(fetchMock);
    expect(urlCalled).toContain('comunicaapi.pje.jus.br');
    expect(urlCalled).not.toContain('djen-proxy');
  });

  it('AbortSignal aborts the in-flight fetch', async () => {
    // `openapi-fetch` passes a single `Request` instance to `fetch`, with the
    // AbortSignal attached to that Request. The mock has to listen to
    // `request.signal` rather than `init?.signal`.
    const fetchMock = vi.fn().mockImplementation(
      (input: RequestInfo | URL, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          const signal =
            input instanceof Request ? input.signal : init?.signal;
          if (signal) {
            if (signal.aborted) {
              const err = new Error('aborted');
              err.name = 'AbortError';
              reject(err);
              return;
            }
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
  });
});
