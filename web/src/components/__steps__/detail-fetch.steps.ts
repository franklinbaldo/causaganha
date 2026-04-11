import { describe, it, expect, vi } from 'vitest';
import { fetchLivePublicationDetail } from '../../lib/djen';

describe('fetchLivePublicationDetail', () => {
  it('should return djen source on success', async () => {
    // Mock fetch to succeed
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: [{ id: 1, numeroComunicacao: 123, siglaTribunal: 'TJSP', texto: 'live data' }]
      })
    });

    const mockPub = { numeroComunicacao: 123, siglaTribunal: 'TJSP', texto: 'old data' } as any;

    const result = await fetchLivePublicationDetail(mockPub);
    expect(result.source).toBe('djen');
    expect(result.usedFallback).toBe(false);
    expect(result.publication?.texto).toBe('live data');
  });

  it('should fallback to ia source on fetch failure', async () => {
    // Mock fetch to fail
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

    const mockPub = { numeroComunicacao: 123, siglaTribunal: 'TJSP', texto: 'old data' } as any;

    const result = await fetchLivePublicationDetail(mockPub);
    expect(result.source).toBe('ia');
    expect(result.usedFallback).toBe(true);
    expect(result.publication?.texto).toBe('old data');
  });

  it('should fallback to ia source when returning no items', async () => {
    // Mock fetch to succeed but return empty items
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        items: []
      })
    });

    const mockPub = { numeroComunicacao: 123, siglaTribunal: 'TJSP', texto: 'old data' } as any;

    const result = await fetchLivePublicationDetail(mockPub);
    expect(result.source).toBe('ia');
    expect(result.usedFallback).toBe(true);
    expect(result.publication?.texto).toBe('old data');
  });
});
