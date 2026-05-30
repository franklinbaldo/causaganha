import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchWithRetry } from './fetchData';

describe('fetchWithRetry', () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('starts a new browser retry after a request times out', async () => {
    vi.useFakeTimers();

    const fetchMock = vi.fn((_url: string | URL | Request, init?: RequestInit) => {
      const signal = init?.signal;

      return new Promise<Response>((_resolve, reject) => {
        signal?.addEventListener('abort', () => {
          reject(signal.reason ?? new DOMException('Aborted', 'AbortError'));
        }, { once: true });
      });
    });

    vi.stubGlobal('fetch', fetchMock);

    const request = fetchWithRetry('https://example.test/data.json', {}, 2, 100);
    request.catch(() => {});

    expect(fetchMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(100);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1000);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(100);
    await expect(request).rejects.toMatchObject({ name: 'TimeoutError' });
  });
});
