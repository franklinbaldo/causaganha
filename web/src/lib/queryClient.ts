import { QueryClient } from '@tanstack/svelte-query';

let _client: QueryClient | null = null;

export function getQueryClient(): QueryClient {
  if (!_client) {
    _client = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 15_000,
          gcTime: 5 * 60 * 1000,
          retry: 2,
          refetchOnWindowFocus: true,
        },
      },
    });
  }
  return _client;
}
