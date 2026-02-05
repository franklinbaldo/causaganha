import { useState, useEffect } from 'react'
import { Terminal, AlertTriangle } from 'lucide-react'
import { LiveStatusCard } from './LiveStatusCard'
import { DualProgressCard } from './DualProgressCard'
import { CalendarHeatmap } from './CalendarHeatmap'
import { TribunalsGrid } from './TribunalsGrid'
import { LastRunDetails } from './LastRunDetails'
import { TimelineGraph } from './TimelineGraph'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [collectProgress, setCollectProgress] = useState(null)
  const [consolidateProgress, setConsolidateProgress] = useState(null)
  const [backfillProgress, setBackfillProgress] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStats = async () => {
    try {
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

      // Fetch progress data (from local build artifact)
      const progressResponse = await fetch('/causaganha/dashboard-data.json');
      if (progressResponse.ok) {
        const data = await progressResponse.json();
        setCollectProgress(data.collect_progress);
        setConsolidateProgress(data.consolidate_progress);
        setBackfillProgress(data.backfill_progress);
      } else {
        console.warn("Progress data not available");
        setCollectProgress(null);
        setConsolidateProgress(null);
        setBackfillProgress(null);
      }
    } catch (error) {
      console.error("Error loading data", error);
      setError("Unable to connect to data source.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-cyber-black text-cyber-primary flex items-center justify-center font-mono">
        <span className="animate-pulse">INITIALIZING SYSTEM...</span>
      </div>
    );
  }

  if (error || (!stats && !collectProgress && !consolidateProgress)) {
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

  return (
    <div className="min-h-screen bg-cyber-black text-cyber-text p-4 md:p-8 font-mono bg-cyber-grid-bg">
      <header className="mb-8 flex justify-between items-center border-b border-cyber-dim pb-4">
        <div className="flex items-center gap-3">
          <Terminal className="w-8 h-8 text-cyber-primary" />
          <div>
            <h1 className="text-2xl font-bold tracking-widest text-cyber-primary">
              CAUSA<span className="text-white">GANHA</span>{' '}
              <span className="text-xs align-top text-cyber-secondary">v2.0</span>
            </h1>
            <p className="text-xs text-cyber-muted uppercase tracking-widest">
              Judicial Data Intelligence Pipeline
            </p>
          </div>
        </div>
        <div className="text-right text-xs text-cyber-muted hidden sm:block">
          <div className="flex items-center gap-2 justify-end">
            <span className="w-2 h-2 bg-cyber-primary rounded-full animate-pulse"></span>
            SYSTEM ONLINE
          </div>
          <div>{new Date().toISOString().split('T')[0]}</div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* Row 1: Key Metrics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <LiveStatusCard stats={stats} />
          </div>
          <div className="lg:col-span-2">
            <DualProgressCard 
              collectProgress={collectProgress}
              consolidateProgress={consolidateProgress}
            />
          </div>
        </div>

        {/* Row 2: Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <CalendarHeatmap data={backfillProgress?.daily_stats || []} />
          </div>
          <div className="lg:col-span-1">
            <TimelineGraph data={backfillProgress?.recent_activity || []} />
          </div>
        </div>

        {/* Row 3: Grid */}
        <TribunalsGrid stats={stats} />

        {/* Row 4: Details */}
        <LastRunDetails stats={stats} />

        {/* About Section */}
        <div className="mt-8 border border-cyber-dim bg-cyber-card p-6 rounded">
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

        <footer className="mt-12 text-center text-xs text-cyber-muted border-t border-cyber-dim pt-6 pb-2">
          <p>CAUSAGANHA MONITORING SYSTEM // AUTHORIZED ACCESS ONLY</p>
          <p className="mt-2 opacity-50">
            Running on GitHub Actions • Data stored in Internet Archive
          </p>
          {backfillProgress?.last_updated && (
              <p className="mt-1 text-cyber-dark opacity-70">
                  Data generated at: {new Date(backfillProgress.last_updated).toLocaleString()} (UTC)
              </p>
          )}
        </footer>
      </div>
    </div>
  );
}
