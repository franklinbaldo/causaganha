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

async function safeFetch(url) {
  try {
    const res = await fetch(url);
    if (res.ok) return res.json();
  } catch { /* swallow */ }
  return null;
}

/**
 * Fetch all data sources. Works both server-side and client-side.
 * For server-side (Astro build), pass a custom fetcher that reads from the filesystem.
 */
export async function fetchAllData() {
  const [stats, dashboardData, today, calendar, runs, backfill] = await Promise.all([
    safeFetch(resolve('run-stats.json')),
    safeFetch(resolve('dashboard-data.json')),
    safeFetch(resolve('cache/today.json')),
    safeFetch(resolve('cache/calendar.json')),
    safeFetch(resolve('cache/runs.json')),
    safeFetch(resolve('cache/backfill.json')),
  ]);

  const cacheData = {};
  if (today) cacheData.today = today;
  if (calendar) cacheData.calendar = calendar;
  if (runs) cacheData.runs = runs;
  if (backfill) cacheData.backfill = backfill;

  const cache = Object.keys(cacheData).length > 0 ? cacheData : null;

  return deriveData(stats, dashboardData, cache);
}

/**
 * Derive all computed data from raw sources.
 * Extracted from Dashboard.jsx to be reusable.
 */
export function deriveData(stats, dashboardData, cacheData) {
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
