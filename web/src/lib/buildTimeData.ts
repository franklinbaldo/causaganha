/**
 * Build-time data loading — server-only.
 * Reads the same sources as fetchAllData() but synchronously via readJson().
 *
 * ONLY import from .astro frontmatter. Never import in .svelte files or
 * any .ts reachable from client code — readJson() pulls in node:fs which
 * does not exist in the browser bundle.
 */
import { readJson } from './readJson';
import { deriveData, type DerivedData, type CacheData } from './fetchData';

export function loadBuildTimeData(): DerivedData {
  // Static files — mirrors the first Promise.all in fetchAllData()
  const stats               = readJson('run-stats.json');
  const dashboardData       = readJson('dashboard-data.json');
  const tribunalStartDates  = readJson('tribunal_start_dates.json');
  const tribunalQualityScores = readJson('tribunal_quality_scores.json');
  const perfMetrics         = readJson('perf-metrics.json');

  // Cache files — mirrors the server-side branch of fetchAllData()
  const today    = readJson('cache/today.json');
  const calendar = readJson('cache/calendar.json');
  const runs     = readJson('cache/runs.json');
  const backfill = readJson('cache/backfill.json');
  const iaSnapshot = readJson('ia-snapshot.json');

  const cacheData: CacheData = {};
  if (today)    cacheData.today    = today;
  if (calendar) cacheData.calendar = calendar;
  if (runs)     cacheData.runs     = runs;
  if (backfill) cacheData.backfill = backfill;
  const cache: CacheData | null = Object.keys(cacheData).length > 0 ? cacheData : null;

  return deriveData(stats, dashboardData, cache, tribunalStartDates, tribunalQualityScores, perfMetrics, iaSnapshot);
}
