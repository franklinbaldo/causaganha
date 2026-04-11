import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchLivePublicationDetail, clearDjenSearchCache } from '../../lib/djen';

function mockResponse(
  body: unknown,
  init: { status?: number; headers?: Record<string, string> } = {},
): Response {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: init.headers,
  });
}

describe('fetchLivePublicationDetail', () => {
  beforeEach(() => {
    clearDjenSearchCache();
  });

  it('should return djen source on success', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse({
        items: [
          { id: 1, numeroComunicacao: 123, siglaTribunal: 'TJSP', texto: 'live data' },
        ],
      }),
    );
    global.fetch = fetchMock as unknown as typeof fetch;

    const mockPub = {
      numeroComunicacao: 123,
      siglaTribunal: 'TJSP',
      texto: 'old data',
    } as any;

    const result = await fetchLivePublicationDetail(mockPub);
    expect(result.source).toBe('djen');
    expect(result.usedFallback).toBe(false);
    expect(result.publication?.texto).toBe('live data');
  });

  it('should fallback to ia source on fetch failure', async () => {
    // TypeError mirrors the shape `fetch` throws on network / CORS failures.
    // Any non-geo-block error would propagate to the caller, so we use a
    // TypeError here to match the classification in djenClient.isGeoBlockShape.
    // The proxy also rejects so the fallback attempt fails and the caller
    // falls back to the IA copy as the ultimate source.
    global.fetch = vi
      .fn()
      .mockRejectedValue(new TypeError('Network error')) as unknown as typeof fetch;

    const mockPub = {
      numeroComunicacao: 123,
      siglaTribunal: 'TJSP',
      texto: 'old data',
    } as any;

    const result = await fetchLivePublicationDetail(mockPub);
    expect(result.source).toBe('ia');
    expect(result.usedFallback).toBe(true);
    expect(result.publication?.texto).toBe('old data');
  });

  it('should fallback to ia source when returning no items', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ items: [] }));
    global.fetch = fetchMock as unknown as typeof fetch;

    const mockPub = {
      numeroComunicacao: 123,
      siglaTribunal: 'TJSP',
      texto: 'old data',
    } as any;

    const result = await fetchLivePublicationDetail(mockPub);
    expect(result.source).toBe('ia');
    expect(result.usedFallback).toBe(true);
    expect(result.publication?.texto).toBe('old data');
  });
});
