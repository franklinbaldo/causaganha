/**
 * Shared data fetching module for CausaGanha Dashboard.
 * Used by Astro pages (build-time) and React islands (client-side refresh).
 *
 * Client-side: fetches live data from Internet Archive (causaganha-dashboard item),
 * falling back to static files bundled at build time.
 * Server-side (Astro build): uses local static files only.
 */

const BASE = import.meta.env.BASE_URL ?? '/causaganha/';
const IA_BASE = 'https://archive.org/download/causaganha-dashboard/';

// Cache file mapping: IA filename -> local path
const IA_CACHE_FILES = {
  'today.json': 'cache/today.json',
  'calendar.json': 'cache/calendar.json',
  'runs.json': 'cache/runs.json',
  'backfill.json': 'cache/backfill.json',
  'meta.json': 'cache/meta.json',
};

function resolve(path) {
  // In Node/build context, fetch from the public dir via relative paths
  if (typeof window === 'undefined') return path;
  // In browser, resolve relative to base URL
  const base = BASE.endsWith('/') ? BASE : BASE + '/';
  return base + path;
}

function resolveIA(filename) {
  return IA_BASE + filename;
}

export async function fetchWithRetry(url, options = {}, maxRetries = 5) {
  let lastError;
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

  let slowTimer;
  if (isBrowser) {
    slowTimer = setTimeout(() => {
      window.dispatchEvent(new CustomEvent('cg-network-slow'));
    }, 10000);
  }

  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(url, options);
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
        const delay = Math.min(1000 * Math.pow(3, i), 30000);
        if (isBrowser) {
          window.dispatchEvent(new CustomEvent('cg-network-retry', {
            detail: { attempt: i + 1, maxRetries, delay }
          }));
        }
        await new Promise(r => setTimeout(r, delay));
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

async function safeFetch(url) {
  try {
    const res = await fetchWithRetry(url);
    if (res && res.ok) return await res.json();
  } catch (err) {
    console.error(`Failed to fetch ${url}:`, err);
  }
  return null;
}

/**
 * Read a JSON file from the filesystem (build-time only).
 * Falls back to null if the file doesn't exist.
 */
async function readLocalJson(relativePath) {
  if (typeof window !== 'undefined') return null;
  try {
    const { readFileSync } = await import('node:fs');
    const { resolve: resolvePath } = await import('node:path');
    const { fileURLToPath } = await import('node:url');
    // dashboard/public/ is the static assets dir
    const publicDir = resolvePath(fileURLToPath(import.meta.url), '../../../public');
    const content = readFileSync(resolvePath(publicDir, relativePath), 'utf-8');
    return JSON.parse(content);
  } catch {
    return null;
  }
}

/**
 * Fetch all data sources. Works both server-side and client-side.
 * Client-side: tries Internet Archive first for live cache data, falls back to static files.
 * Server-side (Astro build): uses local static files only.
 */
export async function fetchAllData() {
  const isBrowser = typeof window !== 'undefined';

  // Static files
  const fetchOrRead = isBrowser ? (path) => safeFetch(resolve(path)) : (path) => readLocalJson(path);
  const [stats, dashboardData, tribunalStartDates, tribunalQualityScores, perfMetrics] =
    await Promise.all([
      fetchOrRead('run-stats.json'),
      fetchOrRead('dashboard-data.json'),
      fetchOrRead('tribunal_start_dates.json'),
      fetchOrRead('tribunal_quality_scores.json'),
      fetchOrRead('perf-metrics.json'),
    ]);

  // Cache files: browser fetches from IA (live), build-time reads from filesystem
  let today, calendar, runs, backfill;
  if (isBrowser) {
    [today, calendar, runs, backfill] = await Promise.all([
      safeFetch(resolveIA('today.json')).then(d => d || safeFetch(resolve('cache/today.json'))),
      safeFetch(resolveIA('calendar.json')).then(d => d || safeFetch(resolve('cache/calendar.json'))),
      safeFetch(resolveIA('runs.json')).then(d => d || safeFetch(resolve('cache/runs.json'))),
      safeFetch(resolveIA('backfill.json')).then(d => d || safeFetch(resolve('cache/backfill.json'))),
    ]);
  } else {
    // Build-time: read directly from filesystem (fetch with relative URLs doesn't work in Node)
    [today, calendar, runs, backfill] = await Promise.all([
      readLocalJson('cache/today.json'),
      readLocalJson('cache/calendar.json'),
      readLocalJson('cache/runs.json'),
      readLocalJson('cache/backfill.json'),
    ]);
  }

  const cacheData = {};
  if (today) cacheData.today = today;
  if (calendar) cacheData.calendar = calendar;
  if (runs) cacheData.runs = runs;
  if (backfill) cacheData.backfill = backfill;

  const cache = Object.keys(cacheData).length > 0 ? cacheData : null;

  return deriveData(stats, dashboardData, cache, tribunalStartDates, tribunalQualityScores,
    perfMetrics);
}

/**
 * Start polling for live data updates from Internet Archive.
 * Calls the callback with new derived data whenever it changes.
 * Returns a cleanup function to stop polling.
 */
export function startLivePolling(onUpdate, intervalMs = 3 * 60 * 1000) {
  if (typeof window === 'undefined') return () => {};

  let lastMetaGenerated = null;

  const poll = async () => {
    try {
      // Quick check: did meta.json change?
      const meta = await safeFetch(resolveIA('meta.json'));
      if (meta && meta.generated_at === lastMetaGenerated) return; // no change
      if (meta) lastMetaGenerated = meta.generated_at;

      // Full refresh
      const data = await fetchAllData();
      onUpdate(data);
    } catch {
      // Silent fail — will retry next interval
    }
  };

  const id = setInterval(poll, intervalMs);
  return () => clearInterval(id);
}

/**
 * Derive all computed data from raw sources.
 * Extracted from Dashboard.jsx to be reusable.
 */
export function deriveData(stats, dashboardData, cacheData, tribunalStartDates = null, tribunalQualityScores = null, perfMetrics = null) {
  const hasAnyData = !!(stats || dashboardData || cacheData);

  // Effective backfill data: merge dashboard-data.json with cache/backfill.json
  // cache/backfill.json is generated from live Internet Archive data and takes precedence;
  // dashboard-data.json is a fallback generated from an ephemeral DuckDB artifact.
  const cacheBackfill = cacheData?.backfill || null;
  const effectiveBackfill = (() => {
    if (dashboardData && cacheBackfill) {
      // Merge: dashboardData as base, cache backfill (live data) takes precedence
      return { ...dashboardData, ...cacheBackfill };
    }
    return cacheBackfill || dashboardData || null;
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
    perfMetrics,
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
