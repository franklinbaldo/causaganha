import { useState, useEffect } from 'react'
import { Terminal, AlertTriangle } from 'lucide-react'
import { LiveStatusCard } from './LiveStatusCard'
import { BackfillProgressCard } from './BackfillProgressCard'
import { DualProgressCard } from './DualProgressCard'
import { CalendarHeatmap } from './CalendarHeatmap'
import { TribunalsGrid } from './TribunalsGrid'
import { LastRunDetails } from './LastRunDetails'
import { TimelineGraph } from './TimelineGraph'
import { ETACard } from './ETACard'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [dashboardData, setDashboardData] = useState(null)
  const [cacheData, setCacheData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

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
      const [todayRes, calendarRes, runsRes] = await Promise.all([
        fetch('./cache/today.json'),
        fetch('./cache/calendar.json'),
        fetch('./cache/runs.json'),
      ]);
      const cache = {};
      if (todayRes.ok) cache.today = await todayRes.json();
      if (calendarRes.ok) cache.calendar = await calendarRes.json();
      if (runsRes.ok) cache.runs = await runsRes.json();
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
    const interval = setInterval(() => fetchStats(false), 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (error || (!loading && !stats && !dashboardData)) {
      return (
        <div className="min-h-screen bg-cyber-black text-cyber-danger flex flex-col items-center justify-center font-mono p-4 text-center">
            <AlertTriangle className="w-16 h-16 mb-4 animate-pulse" />
            <h1 className="text-2xl font-bold mb-2">SYSTEM OFFLINE</h1>
            <p className="text-cyber-muted mb-6">Unable to load dashboard data. The system may be undergoing maintenance.</p>
            <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 border border-cyber-primary text-cyber-primary hover:bg-cyber-primary hover:text-cyber-black transition-colors rounded uppercase text-sm tracking-widest"
            >
                Retry Connection
            </button>
        </div>
      )
  }

  const backfillProgress = dashboardData?.backfill_progress;

  // Derive calendar heatmap data: prefer DuckDB daily_stats, fall back to cache calendar
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

  // Derive timeline data: prefer DuckDB recent_activity, fall back to last 7 days of cache calendar
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

  // Enrich stats.tribunals with cache data (last_update, doc_count from manifest)
  const enrichedStats = (() => {
    const base = stats || {};
    const cacheTribunals = cacheData?.today?.tribunal_status;
    if (!cacheTribunals) return base;
    // Map cache format (ok/absent/pending) to dashboard format (success/absent/error)
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

  // Pipeline health from cache
  const pipelineHealth = cacheData?.runs?.health ?? null;

  return (
    <div className="min-h-screen bg-cyber-black text-cyber-text p-4 md:p-8 font-mono bg-cyber-grid-bg">
      <header className="mb-8 flex justify-between items-center border-b border-cyber-border pb-4">
        <div className="flex items-center gap-3">
          <Terminal className="w-8 h-8 text-cyber-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-widest text-cyber-primary">
              CAUSA<span className="text-white">GANHA</span>{' '}
              <span className="text-sm align-top text-cyber-secondary font-bold">v2.0</span>
            </h1>
            <p className="text-base text-cyber-gray uppercase tracking-widest font-bold">
              Judicial Data Intelligence Pipeline
            </p>
          </div>
        </div>
        <div className="text-right text-sm text-cyber-gray hidden sm:block font-medium">
          <div className="flex items-center gap-2 justify-end">
            <span className="w-2.5 h-2.5 bg-cyber-primary rounded-full animate-pulse"></span>
            SYSTEM ONLINE
            {pipelineHealth !== null && (
              <span className="ml-2 text-cyber-text">{pipelineHealth}%</span>
            )}
          </div>
          <div>{new Date().toISOString().split('T')[0]}</div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Row 1: ETA Highlight (Prominent) */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <div className="lg:col-span-2">
            <ETACard backfillProgress={dashboardData} />
          </div>
          <div className="lg:col-span-2">
            <DualProgressCard apiUrl="./dashboard-data.json" refreshInterval={60000} />
          </div>
        </div>

        {/* Row 2: Status & Stats */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <LiveStatusCard stats={stats} cacheToday={cacheData?.today} />
          </div>
          <div className="lg:col-span-2">
            <CalendarHeatmap data={calendarData} />
          </div>
        </div>

        {/* Row 3: Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-3">
            <TimelineGraph data={timelineData} />
          </div>
        </div>

        {/* Row 4: Grid */}
        <TribunalsGrid stats={enrichedStats} loading={loading} refreshing={refreshing} />

        {/* Row 5: Details */}
        <LastRunDetails stats={stats} />

        {/* About Section */}
        <div className="mt-8 border border-cyber-border bg-cyber-card p-6 rounded">
          <h2 className="text-cyber-primary text-lg font-bold mb-3 tracking-widest">
            // SOBRE O PROJETO
          </h2>
          <div className="text-cyber-text text-sm space-y-3">
            <p>
              O <span className="text-cyber-primary font-bold">CausaGanha</span> coleta dados
              estruturados de comunicações judiciais (DJEN) de 91 tribunais brasileiros a cada 5
              minutos, arquivando no Internet Archive.
            </p>
            <p>
              <span className="text-cyber-secondary font-bold">Missão:</span> Eliminar assimetria
              de informação no mercado jurídico através de ratings transparentes de performance de
              advogados baseados em dados.
            </p>
            <div className="flex gap-4 mt-4 flex-wrap">
              <a
                href="https://github.com/franklinbaldo/causaganha"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyber-primary hover:text-white border border-cyber-primary hover:border-white px-4 py-2 rounded transition-colors"
              >
                → GitHub
              </a>
              <a
                href="https://archive.org/search?query=creator%3A%22causaganha%22"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyber-primary hover:text-white border border-cyber-primary hover:border-white px-4 py-2 rounded transition-colors"
              >
                → Internet Archive
              </a>
            </div>
          </div>
        </div>

        <footer className="mt-12 text-center text-sm text-cyber-gray border-t border-cyber-border pt-6 pb-2">
          <p className="font-bold tracking-widest">CAUSAGANHA MONITORING SYSTEM // AUTHORIZED ACCESS ONLY</p>
          <p className="mt-2 text-cyber-muted font-medium">
            Running on GitHub Actions • Data stored in Internet Archive
          </p>
          {backfillProgress?.last_updated && (
              <p className="mt-1 text-cyber-muted font-medium">
                  Data generated at: {new Date(backfillProgress.last_updated).toLocaleString()} (UTC)
              </p>
          )}
        </footer>
      </div>
    </div>
  );
}
