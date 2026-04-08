import { vi } from 'vitest';

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
