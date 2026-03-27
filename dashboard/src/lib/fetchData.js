/**
 * Shared data fetching module for CausaGanha Dashboard.
 * Used by Astro pages (build-time) and React islands (client-side refresh).
 *
 * 3-tier fallback: dashboard-data.json > cache/backfill.json > empty state
 */

const BASE = import.meta.env.BASE_URL ?? '/causaganha/';

function resolve(path) {
  // In Node/build context, fetch from the public dir via relative paths
  if (typeof window === 'undefined') return path;
  // In browser, resolve relative to base URL
  const base = BASE.endsWith('/') ? BASE : BASE + '/';
  return base + path;
}

export async function fetchWithRetry(url, options = {}, maxRetries = 6) {
  let lastError;
  const isBrowser = typeof window !== 'undefined';
  const delays = [1000, 3000, 9000, 27000, 27000];

  if (!isBrowser) {
    try {
      const response = await fetch(url, options);
      return response;
    } catch {
      return { ok: false, status: 500, json: async () => ({}) };
    }
  }

  let slowTimer;
  if (isBrowser) {
    slowTimer = setTimeout(() => {
      window.dispatchEvent(new CustomEvent('cg-network-slow'));
    }, 10000);
  }

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        if ([429, 502, 503, 504].includes(response.status)) {
          throw new Error(`Transient HTTP Error: ${response.status}`);
        } else if (response.status >= 400 && response.status < 500) {
          // Do NOT retry definitive client errors
          const err = new Error(`Definitive HTTP Error: ${response.status}`);
          err.isDefinitive = true;
          throw err;
        } else if (response.status >= 500) {
          throw new Error(`HTTP Error: ${response.status}`);
        }
      }

      if (isBrowser) {
        clearTimeout(slowTimer);
        window.dispatchEvent(new CustomEvent('cg-network-success'));
      }
      return response;
    } catch (error) {
      if (error.name === 'AbortError') {
        if (isBrowser) clearTimeout(slowTimer);
        throw error; // Bubble up immediately without retry
      }
      if (error.isDefinitive) {
        if (isBrowser) clearTimeout(slowTimer);
        throw error;
      }

      lastError = error;
      if (i < maxRetries - 1) {
        const delay = delays[i] || delays[delays.length - 1];
        if (isBrowser) {
          window.dispatchEvent(new CustomEvent('cg-network-retry', {
            detail: { attempt: i + 1, maxRetries: delays.length, delay }
          }));
        }

        // Wait for delay or abort
        await new Promise((resolve, reject) => {
          let timeoutId;
          const onAbort = () => {
            clearTimeout(timeoutId);
            reject(new DOMException('Aborted', 'AbortError'));
          };

          if (options.signal) {
            if (options.signal.aborted) return onAbort();
            options.signal.addEventListener('abort', onAbort);
          }

          timeoutId = setTimeout(() => {
            if (options.signal) options.signal.removeEventListener('abort', onAbort);
            resolve();
          }, delay);
        });
      }
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

async function safeFetch(url, options = {}) {
  try {
    const res = await fetchWithRetry(url, options);
    if (res && res.ok) return await res.json();
  } catch (err) {
    if (err.name === 'AbortError') {
      throw err; // Re-throw to caller to stop Promise.all
    }
    console.error(`Failed to fetch ${url}:`, err);
  }
  return null;
}

/**
 * Fetch all data sources. Works both server-side and client-side.
 * For server-side (Astro build), pass a custom fetcher that reads from the filesystem.
 */
export async function fetchAllData(signal) {
  const options = signal ? { signal } : {};
  const [stats, dashboardData, today, calendar, runs, backfill, tribunalStartDates, tribunalQualityScores] = await Promise.all([
    safeFetch(resolve('run-stats.json'), options),
    safeFetch(resolve('dashboard-data.json'), options),
    safeFetch(resolve('cache/today.json'), options),
    safeFetch(resolve('cache/calendar.json'), options),
    safeFetch(resolve('cache/runs.json'), options),
    safeFetch(resolve('cache/backfill.json'), options),
    safeFetch(resolve('tribunal_start_dates.json'), options),
    safeFetch(resolve('tribunal_quality_scores.json'), options),
  ]);

  const cacheData = {};
  if (today) cacheData.today = today;
  if (calendar) cacheData.calendar = calendar;
  if (runs) cacheData.runs = runs;
  if (backfill) cacheData.backfill = backfill;

  const cache = Object.keys(cacheData).length > 0 ? cacheData : null;

  return deriveData(stats, dashboardData, cache, tribunalStartDates, tribunalQualityScores);
}

/**
 * Derive all computed data from raw sources.
 * Extracted from Dashboard.jsx to be reusable.
 */
export function deriveData(stats, dashboardData, cacheData, tribunalStartDates = null, tribunalQualityScores = null) {
  const hasAnyData = !!(stats || dashboardData || cacheData);

  // Effective backfill data: merge dashboard-data.json with cache/backfill.json
  // backfill.json always has the richest data (progress_by_year, tribunal_stats, etc.)
  const cacheBackfill = cacheData?.backfill || null;
  const effectiveBackfill = (() => {
    if (dashboardData && cacheBackfill) {
      // Merge: cache backfill as base, overlay with dashboardData fields
      return { ...cacheBackfill, ...dashboardData };
    }
    return dashboardData || cacheBackfill || null;
  })();
  const backfillProgress = effectiveBackfill?.backfill_progress;
  const tribunalCoverage = effectiveBackfill?.tribunal_coverage || {};
  const tribunalEtas = effectiveBackfill?.tribunal_etas || {};
  const targetRange = effectiveBackfill?.target_range || { start: "2024-01-01", end: "2026-02-03", total_days: 764 };

  // Derive calendar heatmap data
  const calendarData = (() => {
    if (backfillProgress?.daily_stats?.length > 0) return backfillProgress.daily_stats;
    if (cacheData?.calendar?.days) {
      return Object.entries(cacheData.calendar.days).map(([date, info]) => ({
        date,
        count: info.tribunal_count || 0,
      }));
    }
    return [];
  })();

  // Derive timeline data
  const timelineData = (() => {
    if (backfillProgress?.recent_activity?.length > 0) return backfillProgress.recent_activity;
    if (cacheData?.calendar?.days) {
      const entries = Object.entries(cacheData.calendar.days)
        .map(([date, info]) => ({ date, count: info.tribunal_count || 0 }))
        .filter(d => d.count > 0)
        .sort((a, b) => a.date.localeCompare(b.date));
      return entries.slice(-7);
    }
    return [];
  })();

  // Per-year progress data: prefer cache backfill which always has this field
  const progressByYear = effectiveBackfill?.progress_by_year || cacheBackfill?.progress_by_year || null;

  // Enrich stats.tribunals with cache data
  const enrichedStats = (() => {
    const base = stats || {};
    const cacheTribunals = cacheData?.today?.tribunal_status;
    if (!cacheTribunals) return base;
    const statusMap = { ok: 'success', absent: 'absent', pending: 'error' };
    const tribunals = {};
    for (const [name, info] of Object.entries(cacheTribunals)) {
      tribunals[name] = {
        status: statusMap[info.status] || info.status || 'error',
        last_update: info.last_update || null,
        doc_count: info.doc_count || undefined,
        ...(base.tribunals?.[name] || {}),
      };
    }
    return { ...base, tribunals };
  })();

  return {
    stats,
    dashboardData,
    cacheData,
    tribunalStartDates,
    tribunalQualityScores,
    hasAnyData,
    effectiveBackfill,
    backfillProgress,
    calendarData,
    timelineData,
    progressByYear,
    enrichedStats,
    tribunalCoverage,
    tribunalEtas,
    targetRange,
  };
}
