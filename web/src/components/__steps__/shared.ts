import { vi } from 'vitest';
import { render as _render, type RenderResult } from '@testing-library/svelte/pure';
import type { Component } from '@testing-library/svelte-core/types';
import { QueryClient } from '@tanstack/svelte-query';

// Prevent @tanstack/query-devtools from rendering in tests (requires window.matchMedia)
vi.mock('@tanstack/svelte-query-devtools', () => ({
  SvelteQueryDevtools: () => null,
}));

// Provide a fresh QueryClient per test so islands get context without errors.
// fetchAllData is mocked to return null, so queries complete immediately with null data,
// and components fall back to their initialXxx props.
vi.mock('../../lib/queryClient', () => ({
  getQueryClient: () => new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  }),
}));

// Mock fetchAllData for components that import it directly
vi.mock('../../lib/fetchData', () => ({
  fetchAllData: vi.fn().mockResolvedValue(null),
  fetchWithRetry: vi.fn().mockResolvedValue({ ok: false, status: 503, json: async () => ({}) }),
}));

/**
 * Typed wrapper around `@testing-library/svelte`'s `render`.
 *
 * The `@astrojs/svelte` integration rewrites the default export of every
 * `.svelte` file to `(_props: PropsWithClientDirectives<Props>) => any` at
 * type-check time, which no longer matches the modern Svelte 5
 * `Component<P, E>` signature that `render` expects. At runtime the component
 * is still a real Svelte 5 function, so the cast here is safe and lets BDD
 * step files pass Astro-shimmed components directly.
 *
 * The return type is written as `RenderResult<Component<Props>>` rather than
 * `ReturnType<typeof _render>`: `ReturnType` on an uninstantiated generic
 * function drops `_render`'s `Q extends Queries = typeof queries` default,
 * collapsing every bound query (getByText, getByLabelText, ...) to an
 * incompatible union/index-signature type. Naming `RenderResult<C>` directly
 * lets its own `Q` default apply instead.
 */
export const render = _render as unknown as <Props extends Record<string, unknown> = Record<string, unknown>>(
  Component: unknown,
  props?: Props,
  options?: Parameters<typeof _render>[2],
) => RenderResult<Component<Props>>;
