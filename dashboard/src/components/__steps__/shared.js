import { vi } from 'vitest';

// Mock useDataRefresh so components fall back to initial props
vi.mock('../../lib/useDataRefresh', () => ({
  useDataRefresh: () => ({ data: null }),
}));

// Mock fetchAllData for components that import it directly
vi.mock('../../lib/fetchData', () => ({
  fetchAllData: vi.fn().mockResolvedValue(null),
}));
