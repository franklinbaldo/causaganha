import { useState, useEffect } from 'react';
import { Database } from 'lucide-react';
import { BackfillHero } from './BackfillHero';
import { YearProgress } from './YearProgress';
import { ActivityCalendar } from './ActivityCalendar';
import { ActivityChart } from './ActivityChart';
import { TribunalGrid } from './TribunalGrid';
import { SystemStatus } from './SystemStatus';
import { ThemeToggle } from './ThemeToggle';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [cacheData, setCacheData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchStats = async (isInitial = false) => {
    try {
      if (!isInitial) setRefreshing(true);
      setError(null);
      // Fetch run stats
      const statsResponse = await fetch('./run-stats.json');
      if (statsResponse.ok) {
        const data = await statsResponse.json();
        setStats(data);
      } else {
        console.warn("Failed to load run-stats.json");
        setStats(null);
      }

      // Fetch dashboard data (generated from DuckDB)
      const response = await fetch('./dashboard-data.json');
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      } else {
        console.warn("Dashboard data not available");
        setDashboardData(null);
      }

      // Fetch cache data (generated from manifest.parquet - always available)
      const [todayRes, calendarRes, runsRes, backfillRes] = await Promise.all([
        fetch('./cache/today.json'),
        fetch('./cache/calendar.json'),
        fetch('./cache/runs.json'),
        fetch('./cache/backfill.json'),
      ]);
      const cache = {};
      if (todayRes.ok) cache.today = await todayRes.json();
      if (calendarRes.ok) cache.calendar = await calendarRes.json();
      if (runsRes.ok) cache.runs = await runsRes.json();
      if (backfillRes.ok) cache.backfill = await backfillRes.json();
      if (Object.keys(cache).length > 0) setCacheData(cache);
    } catch (error) {
      console.error("Error loading data", error);
      setError("Unable to connect to data source.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats(true);
    const interval = setInterval(() => fetchStats(false), 60000);
    return () => clearInterval(interval);
  }, []);

  // Graceful degradation instead of full-screen error
  const hasAnyData = stats || dashboardData || cacheData;

  // Effective backfill data: prefer DuckDB dashboard-data.json, fall back to cache backfill.json
  const effectiveBackfill = dashboardData || cacheData?.backfill || null;
  const backfillProgress = effectiveBackfill?.backfill_progress;

  // Derive calendar heatmap data: prefer backfill daily_stats, fall back to cache calendar
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

  // Derive timeline data: prefer backfill recent_activity, fall back to last 7 days of cache calendar
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

  // Per-year progress data
  const progressByYear = effectiveBackfill?.progress_by_year || null;

  // Enrich stats.tribunals with cache data (last_update, doc_count from manifest)
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

  return (
    <div className="min-h-screen bg-[var(--color-bg)] p-4 md:p-6 lg:p-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-accent-muted rounded-xl">
            <Database className="w-5 h-5 text-accent" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-content tracking-tight">
              CausaGanha
            </h1>
            <p className="text-sm text-content-tertiary">
              Judicial Data Intelligence Pipeline
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {backfillProgress?.last_updated && (
            <span className="text-xs text-content-tertiary hidden sm:block">
              Updated {new Date(backfillProgress.last_updated).toLocaleString('pt-BR')}
            </span>
          )}
          <ThemeToggle />
        </div>
      </header>

      {/* Error banner (graceful, not full-screen) */}
      {error && !hasAnyData && (
        <div className="max-w-7xl mx-auto mb-6 p-4 bg-danger-muted border border-danger/20 rounded-xl text-center">
          <p className="text-sm text-danger font-medium mb-2">Unable to load dashboard data</p>
          <button
            onClick={() => fetchStats(true)}
            className="text-sm bg-danger text-white px-4 py-1.5 rounded-lg hover:bg-danger-light transition-colors font-medium"
          >
            Retry
          </button>
        </div>
      )}

      <main className="max-w-7xl mx-auto space-y-6">
        {/* Row 1: Hero — Backfill Progress + Year Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3">
            <BackfillHero backfillProgress={effectiveBackfill} />
          </div>
          <div className="lg:col-span-2">
            <YearProgress progressByYear={progressByYear} />
          </div>
        </div>

        {/* Row 2: Activity — Calendar + Recent Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3">
            <ActivityCalendar data={calendarData} />
          </div>
          <div className="lg:col-span-2">
            <ActivityChart data={timelineData} />
          </div>
        </div>

        {/* Row 3: Tribunal Grid */}
        <TribunalGrid stats={enrichedStats} loading={loading} refreshing={refreshing} />

        {/* Row 4: System Status (footer-ish) */}
        <SystemStatus stats={stats} cacheToday={cacheData?.today} />

        {/* Footer */}
        <footer className="text-center text-xs text-content-tertiary pt-4 pb-2">
          <p>Data sourced from DJEN across 91 tribunals. Stored on Internet Archive.</p>
        </footer>
      </main>
    </div>
  );
}
