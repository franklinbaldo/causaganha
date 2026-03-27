import { useState, useEffect, useCallback } from 'react';
import { fetchAllData } from './fetchData';

// Shared client-side cache to avoid duplicate fetches across islands
if (typeof window !== 'undefined' && !window.__CAUSAGANHA_DATA) {
  window.__CAUSAGANHA_DATA = { data: null, timestamp: 0, promise: null, controller: null };
}

const STALE_MS = 15000; // Consider cache stale after 15s

async function fetchShared(force = false) {
  const cache = window.__CAUSAGANHA_DATA;
  const now = Date.now();

  // Return cached data if fresh and not forcing
  if (!force && cache.data && now - cache.timestamp < STALE_MS) {
    return cache.data;
  }

  // Deduplicate concurrent fetches unless forcing
  if (cache.promise) {
    if (force && cache.controller) {
      cache.controller.abort();
      cache.promise = null;
      cache.controller = null;
    } else {
      return cache.promise;
    }
  }

  cache.controller = new AbortController();

  cache.promise = fetchAllData(cache.controller.signal)
    .then(result => {
      cache.data = result;
      cache.timestamp = Date.now();
      cache.promise = null;
      cache.controller = null;
      return result;
    })
    .catch(err => {
      if (err.name !== 'AbortError') {
        cache.promise = null;
        cache.controller = null;
      }
      throw err;
    });

  return cache.promise;
}

// Allow aborting requests completely without starting a new one
export function abortSharedFetch() {
  const cache = window.__CAUSAGANHA_DATA;
  if (cache && cache.controller) {
    cache.controller.abort();
    cache.promise = null;
    cache.controller = null;
  }
}

/**
 * React hook for client-side data refresh.
 * Each island uses this independently; the shared cache prevents duplicate fetches.
 *
 * @param {string} dataKey - Dot-notation key to extract from derived data (e.g. 'enrichedStats')
 * @param {object} initialData - Build-time data passed as prop from Astro
 * @param {number} interval - Refresh interval in ms (default 60s)
 */
export function useDataRefresh(dataKey, initialData = null, interval = 60000) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState(null);

  const refresh = useCallback(async (force = false) => {
    try {
      if (force) setLoading(true);
      setError(null);
      const allData = await fetchShared(force);
      const value = dataKey ? allData[dataKey] : allData;
      setData(value);
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log(`[useDataRefresh] Fetch aborted for ${dataKey || 'all'}`);
        return; // Don't set error state if intentionally aborted
      }
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

    // Listen for manual retries from the NetworkStatusBanner
    const handleManualRetry = () => {
      refresh(true);
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('cg-network-manual-retry', handleManualRetry);
    }

    return () => {
      clearInterval(timer);
      if (typeof window !== 'undefined') {
        window.removeEventListener('cg-network-manual-retry', handleManualRetry);
      }
    };
  }, [refresh, interval, initialData]);

  return { data, loading, error, refresh };
}
