import { vi } from 'vitest';
import { render as _render } from '@testing-library/svelte/pure';

// Mock dataRefreshStore so components fall back to initial props
vi.mock('../../lib/dataRefreshStore', () => ({
  createDataRefresh: () => ({
    subscribe: (fn: (val: any) => void) => {
      fn({ data: null, loading: false, error: null });
      return () => {};
    },
    refresh: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  }),
}));

// Mock fetchAllData for components that import it directly
vi.mock('../../lib/fetchData', () => ({
  fetchAllData: vi.fn().mockResolvedValue(null),
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
 */
export const render = _render as unknown as <Props = Record<string, unknown>>(
  Component: unknown,
  props?: Props,
  options?: Parameters<typeof _render>[2],
) => ReturnType<typeof _render>;
