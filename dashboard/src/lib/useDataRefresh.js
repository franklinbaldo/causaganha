import { useState, useEffect, useCallback } from 'react';
import { fetchAllData } from './fetchData';

// Shared client-side cache to avoid duplicate fetches across islands
if (typeof window !== 'undefined' && !window.__CAUSAGANHA_DATA) {
  window.__CAUSAGANHA_DATA = { data: null, timestamp: 0, promise: null };
}

const STALE_MS = 15000; // Consider cache stale after 15s

async function fetchShared() {
  const cache = window.__CAUSAGANHA_DATA;
  const now = Date.now();

  // Return cached data if fresh
  if (cache.data && now - cache.timestamp < STALE_MS) {
    return cache.data;
  }

  // Deduplicate concurrent fetches
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

/**
 * React hook for client-side data refresh.
 * Each island uses this independently; the shared cache prevents duplicate fetches.
 *
 * @param {string} dataKey - Dot-notation key to extract from derived data (e.g. 'enrichedStats')
 * @param {object} initialData - Build-time data passed as prop from Astro
 * @param {number} interval - Refresh interval in ms (default 60s)
 */
export function useDataRefresh(dataKey, initialData = null, interval = 30000) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);

  const refresh = useCallback(async (isInitial = false) => {
    try {
      if (!isInitial) setLoading(false); // Don't show loading on refresh
      setError(null);
      const allData = await fetchShared();
      const value = dataKey ? allData[dataKey] : allData;
      setData(value);
    } catch (err) {
      console.error(`[useDataRefresh] Error fetching ${dataKey}:`, err);
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  }, [dataKey]);

  useEffect(() => {
    // Initial fetch (unless we have build-time data)
    if (!initialData) {
      refresh(true);
    } else {
      // Still kick off a background refresh to get fresh data
      refresh(false);
    }

    const timer = setInterval(() => refresh(false), interval);
    return () => clearInterval(timer);
  }, [refresh, interval, initialData]);

  return { data, loading, error, refresh };
}
