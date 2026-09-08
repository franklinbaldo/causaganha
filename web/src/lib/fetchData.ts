/**
 * Shared HTTP-fetch helper for CausaGanha Dashboard client-side islands.
 *
 * Build-time data loading goes through `loadContract()` (query contracts,
 * see CLAUDE.md) and `readJson()` instead of this module.
 */

interface FallbackResponse {
  ok: false;
  status: number;
  json: () => Promise<Record<string, never>>;
}

export async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  maxRetries: number = 5,
  timeoutMs: number = 15000,
): Promise<Response | FallbackResponse> {
  let lastError: unknown;
  const isBrowser = typeof window !== 'undefined';

  // Astro build uses relative URLs via resolve(), node-fetch requires absolute URLs
  // The original fetch simply suppressed errors, but fetchWithRetry throws on absolute URL error.
  if (!isBrowser) {
    try {
      const response = await fetch(url, options);
      return response;
    } catch {
      // Return a dummy error response or simply fail fast without retry
      // This is expected during build time if using relative paths in node.
      return { ok: false, status: 500, json: async () => ({}) };
    }
  }

  let slowTimer: ReturnType<typeof setTimeout> | undefined;
  if (isBrowser) {
    slowTimer = setTimeout(() => {
      window.dispatchEvent(new CustomEvent('cg-network-slow'));
    }, 10000);
  }

  for (let i = 0; i < maxRetries; i++) {
    const attemptController = new AbortController();
    let timeoutTimer: ReturnType<typeof setTimeout> | undefined;
    let cleanupCombinedSignal = (): void => {};
    let fetchOptions = options;
    let retryDelay: number | undefined;

    try {
      timeoutTimer = setTimeout(() => {
        attemptController.abort(new DOMException(`Fetch timed out after ${timeoutMs}ms`, 'TimeoutError'));
      }, timeoutMs);

      if (options.signal) {
        const combinedController = new AbortController();
        const abortCombined = (signal: AbortSignal): void => {
          if (!combinedController.signal.aborted) {
            combinedController.abort(signal.reason);
          }
        };
        const abortFromOptions = (): void => abortCombined(options.signal as AbortSignal);
        const abortFromTimeout = (): void => abortCombined(attemptController.signal);

        options.signal.addEventListener('abort', abortFromOptions, { once: true });
        attemptController.signal.addEventListener('abort', abortFromTimeout, { once: true });
        cleanupCombinedSignal = (): void => {
          options.signal?.removeEventListener('abort', abortFromOptions);
          attemptController.signal.removeEventListener('abort', abortFromTimeout);
        };

        if (options.signal.aborted) {
          abortCombined(options.signal);
        } else if (attemptController.signal.aborted) {
          abortCombined(attemptController.signal);
        }

        fetchOptions = { ...options, signal: combinedController.signal };
      } else {
        fetchOptions = { ...options, signal: attemptController.signal };
      }

      const response = await fetch(url, fetchOptions);
      if (!response.ok && response.status >= 500) {
        throw new Error(`HTTP Error: ${response.status}`);
      }
      if (isBrowser) {
        clearTimeout(slowTimer);
        window.dispatchEvent(new CustomEvent('cg-network-success'));
      }
      return response;
    } catch (error) {
      lastError = error;
      if (i < maxRetries - 1) {
        retryDelay = Math.min(1000 * Math.pow(3, i), 30000);
        if (isBrowser) {
          window.dispatchEvent(new CustomEvent('cg-network-retry', {
            detail: { attempt: i + 1, maxRetries, delay: retryDelay }
          }));
        }
      }
    } finally {
      if (timeoutTimer) clearTimeout(timeoutTimer);
      cleanupCombinedSignal();
    }

    if (retryDelay !== undefined) {
      await new Promise(r => setTimeout(r, retryDelay));
    }
  }

  if (isBrowser) {
    clearTimeout(slowTimer);
    window.dispatchEvent(new CustomEvent('cg-network-error', {
      detail: { error: lastError }
    }));
  }
  throw lastError;
}
