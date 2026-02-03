import { useState, useEffect } from 'react'
import { LiveStatusCard } from './components/LiveStatusCard'
import { BackfillProgress } from './components/BackfillProgress'
import { CalendarHeatmap } from './components/CalendarHeatmap'
import { TribunalsGrid } from './components/TribunalsGrid'
import { LastRunDetails } from './components/LastRunDetails'
import { TimelineGraph } from './components/TimelineGraph'
import { Terminal } from 'lucide-react'

function App() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = async () => {
    try {
      // In dev mode or if file missing, try to fetch mock if needed, but here we just try relative path
      // Note: when running locally via 'npm run dev', run-stats.json must be in public/
      const response = await fetch('./run-stats.json');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      } else {
        console.warn("Failed to load run-stats.json (404). Using fallback for preview.");
        // Fallback mock data for preview if file not generated yet
        setStats({
             run_id: "preview-mode",
             timestamp: new Date().toISOString(),
             status: "success",
             duration_seconds: 0,
             current_date: new Date().toISOString().split('T')[0],
             steps: {},
             tribunals: {}
        });
      }
    } catch (error) {
        console.error("Error loading stats", error);
    } finally {
        setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
      return <div className="min-h-screen bg-cyber-black text-cyber-primary flex items-center justify-center font-mono">
          <span className="animate-pulse">INITIALIZING SYSTEM...</span>
      </div>
  }

  return (
    <div className="min-h-screen bg-cyber-black text-cyber-text p-4 md:p-8 font-mono bg-cyber-grid-bg">
      <header className="mb-8 flex justify-between items-center border-b border-cyber-dim pb-4">
        <div className="flex items-center gap-3">
            <Terminal className="w-8 h-8 text-cyber-primary" />
            <div>
                <h1 className="text-2xl font-bold tracking-widest text-cyber-primary">CAUSA<span className="text-white">GANHA</span> <span className="text-xs align-top text-cyber-secondary">v2.0</span></h1>
                <p className="text-xs text-cyber-muted uppercase tracking-widest">Judicial Data Intelligence Pipeline</p>
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
                <BackfillProgress stats={stats} />
            </div>
        </div>

        {/* Row 2: Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
             <div className="lg:col-span-2">
                <CalendarHeatmap stats={stats} />
             </div>
             <div className="lg:col-span-1">
                <TimelineGraph stats={stats} />
             </div>
        </div>

        {/* Row 3: Grid */}
        <TribunalsGrid stats={stats} />

        {/* Row 4: Details */}
        <LastRunDetails stats={stats} />

        <footer className="mt-12 text-center text-xs text-cyber-muted border-t border-cyber-dim pt-6 pb-2">
            <p>CAUSAGANHA MONITORING SYSTEM // AUTHORIZED ACCESS ONLY</p>
            <p className="mt-2 opacity-50">Running on GitHub Actions • Data stored in Internet Archive</p>
        </footer>
      </div>
    </div>
  )
}

export default App
