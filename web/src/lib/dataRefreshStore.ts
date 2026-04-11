import { writable, type Readable } from 'svelte/store';
import { fetchAllData } from './fetchData';

type DerivedData = Record<string, any>;

declare global {
  interface Window {
    __CAUSAGANHA_DATA: {
      data: DerivedData | null;
      timestamp: number;
      promise: Promise<DerivedData> | null;
    };
  }
}

// Shared client-side cache to avoid duplicate fetches across islands
if (typeof window !== 'undefined' && !window.__CAUSAGANHA_DATA) {
  window.__CAUSAGANHA_DATA = { data: null, timestamp: 0, promise: null };
}

const STALE_MS = 15000;

async function fetchShared(): Promise<DerivedData> {
  const cache = window.__CAUSAGANHA_DATA;
  const now = Date.now();

  if (cache.data && now - cache.timestamp < STALE_MS) {
    return cache.data;
  }

  if (cache.promise) return cache.promise;

  cache.promise = fetchAllData()
    .then(result => {
      cache.data = result;
      cache.timestamp = Date.now();
      cache.promise = null;
      return result;
    })
    .catch(err => {
      cache.promise = null;
      throw err;
    });

  return cache.promise;
}

export interface DataRefreshState {
  data: any;
  loading: boolean;
  error: string | null;
}

export interface DataRefreshStore extends Readable<DataRefreshState> {
  refresh: (isInitial?: boolean) => Promise<void>;
  start: () => void;
  stop: () => void;
}

/**
 * Creates a Svelte store for client-side data refresh.
 * Each island uses this independently; the shared cache prevents duplicate fetches.
 */
export function createDataRefresh(
  dataKey: string,
  initialData: any = null,
  interval: number = 60000,
): DataRefreshStore {
  const { subscribe, update } = writable<DataRefreshState>({
    data: initialData,
    loading: !initialData,
    error: null,
  });

  let timer: ReturnType<typeof setInterval> | null = null;

  async function refresh(isInitial: boolean = false): Promise<void> {
    try {
      if (!isInitial) update(s => ({ ...s, loading: false }));
      update(s => ({ ...s, error: null }));
      const allData = await fetchShared();
      const value = dataKey ? allData[dataKey] : allData;
      update(s => ({ ...s, data: value, loading: false }));
    } catch (err: unknown) {
      console.error(`[dataRefreshStore] Error fetching ${dataKey}:`, err);
      update(s => ({
        ...s,
        error: err instanceof Error ? err.message : 'Failed to fetch data',
        loading: false,
      }));
    }
  }

  function start(): void {
    if (!initialData) {
      refresh(true);
    } else {
      refresh(false);
    }
    timer = setInterval(() => refresh(false), interval);
  }

  function stop(): void {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  return { subscribe, refresh, start, stop };
}
