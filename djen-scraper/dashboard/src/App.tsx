import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Terminal, Activity, Database, Cloud, AlertCircle, Cpu, Globe, ShieldCheck, Gauge } from 'lucide-react';
import './Terminal.css';

const IA_SEARCH_URL = "https://archive.org/advancedsearch.php?q=(identifier:djen-raw-*) OR (identifier:djen-parquet-*)&fl[]=identifier&fl[]=date&fl[]=tribunal&fl[]=total_comunicacoes&fl[]=addeddate&sort[]=addeddate+desc&rows=1000&output=json";
const GITHUB_RUNS_URL = "https://api.github.com/repos/franklinbaldo/causaganha/actions/runs?workflow_id=archive-zips.yml&per_page=15";
const LOCAL_RUNS_URL = "/causaganha/run_stats.json";

interface ActionRun {
  id: number;
  databaseId?: number;
  workflowName?: string;
  name?: string;
  status: string;
  conclusion: string;
  createdAt: string;
  created_at?: string;
  displayTitle?: string;
  display_title?: string;
  url: string;
  html_url?: string;
}

interface TribunalSummary {
  tribunal: string;
  total_dates: number;
  total_records: number;
  total_bytes: number;
  oldest_date: string | null;
  newest_date: string | null;
}

function formatNumber(n: number): string {
  return n.toLocaleString('pt-BR');
}

export default function App() {
  const [tribunais, setTribunais] = useState<TribunalSummary[]>([]);
  const [runs, setRuns] = useState<ActionRun[]>([]);
  const [recentArchives, setRecentArchives] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [booting, setBooting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalRecords: 0,
    totalItems: 0,
    progress: '0',
    successRate: '0',
    newestDate: 'N/A'
  });

  useEffect(() => {
    const timer = setTimeout(() => setBooting(false), 2500);
    return () => clearTimeout(timer);
  }, []);

  const fetchData = async () => {
    try {
      const [iaRes, runsRes] = await Promise.all([
        fetch(IA_SEARCH_URL).catch(() => null),
        fetch(GITHUB_RUNS_URL).catch(() => null)
      ]);

      let iaDataJson: any = null;
      if (iaRes && iaRes.ok) {
        iaDataJson = await iaRes.json();
        const docs = iaDataJson.response.docs;

        const tribunalsMap: Record<string, TribunalSummary> = {};
        const archiveFeedMap: Record<string, any> = {};
        let totalRecords = 0;
        let newestDate = '2000-01-01';

        docs.forEach((doc: any) => {
          const isParquet = doc.identifier.includes('parquet');
          const trib = doc.tribunal || doc.identifier.split('-').pop();
          const date = (doc.date || '').split('T')[0];
          const feedKey = `${date}-${trib}`;

          if (!isParquet) {
            const records = parseInt(doc.total_comunicacoes || '0', 10);
            totalRecords += records;
            if (date > newestDate) newestDate = date;

            if (!tribunalsMap[trib]) {
              tribunalsMap[trib] = {
                tribunal: trib,
                total_dates: 0,
                total_records: 0,
                total_bytes: 0,
                oldest_date: date,
                newest_date: date,
              };
            }

            const summary = tribunalsMap[trib];
            summary.total_dates += 1;
            summary.total_records += records;
            if (date < (summary.oldest_date || '9999')) summary.oldest_date = date;
            if (date > (summary.newest_date || '0000')) summary.newest_date = date;
          }

          if (!archiveFeedMap[feedKey]) {
            archiveFeedMap[feedKey] = {
              tribunal: trib,
              date: date,
              addeddate: doc.addeddate,
              comms: doc.total_comunicacoes,
              zipId: null,
              parquetId: null
            };
          }

          if (isParquet) {
            archiveFeedMap[feedKey].parquetId = doc.identifier;
          } else {
            archiveFeedMap[feedKey].zipId = doc.identifier;
            if (!archiveFeedMap[feedKey].comms) archiveFeedMap[feedKey].comms = doc.total_comunicacoes;
          }
        });

        setTribunais(Object.values(tribunalsMap).sort((a, b) => b.total_records - a.total_records));

        // Sort feed by addeddate desc
        const sortedFeed = Object.values(archiveFeedMap).sort((a, b) =>
          new Date(b.addeddate).getTime() - new Date(a.addeddate).getTime()
        );
        setRecentArchives(sortedFeed.slice(0, 15));

        // Estimate progress: ~91 tribunals * 260 days/year * 4 years (2022-2026)
        const totalTarget = 91 * 260 * 4;
        const progressPct = Math.min(((iaDataJson.response.numFound / totalTarget) * 100), 100).toFixed(1);

        setStats(prev => ({
          ...prev,
          totalRecords,
          totalItems: iaDataJson.response.numFound,
          progress: progressPct,
          newestDate: newestDate
        }));
      }

      if (runsRes && runsRes.ok) {
        const runsData = await runsRes.json();
        const workflowRuns = runsData.workflow_runs || [];
        setRuns(workflowRuns);

        // Calculate success rate from last 15 runs
        const successCount = workflowRuns.filter((r: any) => r.conclusion === 'success').length;
        const rate = ((successCount / Math.max(workflowRuns.length, 1)) * 100).toFixed(0);
        setStats(prev => ({ ...prev, successRate: rate }));

      } else {
        const localRes = await fetch(LOCAL_RUNS_URL).catch(() => null);
        if (localRes && localRes.ok) {
          setRuns(await localRes.json());
        }
      }
      setError(iaRes?.ok ? null : "IA_API_OFFLINE");
    } catch (err) {
      setError(err instanceof Error ? err.message : 'System fault');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (booting) {
    return (
      <div className="min-h-screen bg-black flex flex-col items-center justify-center p-4 crt overflow-hidden">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="w-full max-w-lg font-mono text-green-500"
        >
          <div className="mb-4">DJEN MONITOR v2.1.0</div>
          <div className="mb-2">SYSTEM CLOCK: {new Date().toLocaleTimeString()}</div>
          <div className="mb-4 text-xs opacity-70">UPLINK: SECURE_SOCKET_ESTABLISHED</div>
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: "100%" }}
            transition={{ duration: 2, ease: "linear" }}
            className="h-1 bg-green-500 mb-4"
          />
          <div className="space-y-1 text-sm">
            <div>[ OK ] SUBSYSTEM_INIT</div>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>[ OK ] SCRAPER_METRICS_SYNC</motion.div>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0 }}>[ OK ] IA_COLLECTION_SCAN</motion.div>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }} className="text-white">LOADING INTERFACE...</motion.div>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-[#00ff41] p-2 md:p-6 crt font-mono selection:bg-[#00ff41] selection:text-black">
      <div className="max-w-7xl mx-auto border-2 border-[#00ff41] p-4 bg-black/80 relative overflow-hidden shadow-[0_0_15px_rgba(0,255,65,0.3)]">
        <div className="scanline"></div>

        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center border-b-2 border-[#00ff41] pb-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Terminal className="w-10 h-10 animate-pulse" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
            </div>
            <div>
              <h1 className="text-2xl md:text-5xl font-black terminal-text-shadow tracking-tighter">DJEN_CONTROL_CENTER</h1>
              <p className="text-[10px] opacity-70">SCRAPING_OPERATIONS_MONITOR // {new Date().toLocaleDateString()}</p>
            </div>
          </div>
          <div className="mt-4 md:mt-0 px-4 py-2 border border-[#00ff41] bg-[#00ff41]/10 flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${loading ? 'bg-amber-500 animate-pulse' : 'bg-green-500'}`}></div>
            <span className="text-xs font-bold uppercase tracking-widest">{loading ? 'Syncing...' : 'Link_Live'}</span>
          </div>
        </header>

        {/* Dash Monitor Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          {[
            { label: 'TOTAL_RECORDS', val: formatNumber(stats.totalRecords), icon: Activity, detail: 'Comunicações' },
            { label: 'ARCHIVE_SIZE', val: stats.totalItems, icon: Database, detail: 'Zips no IA' },
            { label: 'COVERAGE', val: `${stats.progress}%`, icon: Gauge, detail: 'Target: 4 Anos' },
            { label: 'HEALTH', val: `${stats.successRate}%`, icon: ShieldCheck, detail: 'Last 15 Runs' },
            { label: 'FRESHNESS', val: stats.newestDate, icon: Globe, detail: 'Data mais recente' }
          ].map((s, i) => (
            <motion.div
              key={i}
              className="p-3 border border-[#00ff41]/40 bg-black/40 hover:border-[#00ff41] transition-all group"
            >
              <div className="flex justify-between items-start mb-1 text-[#00ff41]/60 group-hover:text-[#00ff41]">
                <span className="text-[9px] font-bold tracking-tighter">{s.label}</span>
                <s.icon className="w-3 h-3" />
              </div>
              <div className="text-xl font-bold terminal-text-shadow leading-tight mb-1">{s.val}</div>
              <div className="text-[9px] opacity-40 uppercase">{s.detail}</div>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Feed */}
          <div className="lg:col-span-3 space-y-6">
            <section className="border border-[#00ff41] p-4 relative bg-[#00ff41]/5">
              <div className="absolute top-0 right-0 bg-[#00ff41] text-black px-2 text-[10px] font-bold">LIVE_DATA_FEED</div>
              <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
                <Cloud className="w-4 h-4" /> RECENT_INCOMING_ARCHIVES
              </h2>
              <div className="overflow-x-auto scrollbar-terminal">
                <table className="w-full text-[11px] text-left">
                  <thead className="text-[#00ff41] uppercase border-b border-[#00ff41]/30">
                    <tr>
                      <th className="pb-2">Tribunal</th>
                      <th className="pb-2">Data_Caderno</th>
                      <th className="pb-2">Records</th>
                      <th className="pb-2">Artifacts</th>
                      <th className="pb-2">Archived_At</th>
                    </tr>
                  </thead>
                  <tbody className="opacity-80">
                    {recentArchives.map((doc, idx) => (
                      <tr key={idx} className="border-b border-[#00ff41]/10 hover:bg-[#00ff41]/10 transition-colors">
                        <td className="py-2">
                          <span className="bg-[#00ff41]/10 px-1 border border-[#00ff41]/30">
                            {doc.tribunal}
                          </span>
                        </td>
                        <td className="py-2">{doc.date}</td>
                        <td className="py-2 font-bold">{formatNumber(parseInt(doc.comms || '0'))}</td>
                        <td className="py-2 flex gap-2">
                          {doc.zipId && (
                            <a href={`https://archive.org/details/${doc.zipId}`} target="_blank" rel="noreferrer" className="text-blue-500 hover:text-white underline">
                              [ZIP]
                            </a>
                          )}
                          {doc.parquetId && (
                            <a href={`https://archive.org/details/${doc.parquetId}`} target="_blank" rel="noreferrer" className="text-amber-500 hover:text-white underline">
                              [PARQUET]
                            </a>
                          )}
                        </td>
                        <td className="py-2 opacity-60 text-[10px]">{new Date(doc.addeddate).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <section className="border border-[#00ff41] p-4 bg-black/40">
                <h2 className="text-sm font-bold mb-4 flex items-center gap-2">
                  <Cpu className="w-4 h-4" /> WORKFLOW_EXECUTION_LOG
                </h2>
                <div className="space-y-2 max-h-[300px] overflow-y-auto scrollbar-terminal pr-2">
                  {runs.slice(0, 10).map((run) => (
                    <div key={run.id} className="flex justify-between items-center text-[10px] border-b border-[#00ff41]/10 pb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        {run.conclusion === 'success' ? (
                          <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
                        ) : run.status === 'in_progress' ? (
                          <div className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse"></div>
                        ) : (
                          <div className="w-1.5 h-1.5 bg-red-500 rounded-full"></div>
                        )}
                        <span className="truncate opacity-80">{run.display_title || run.name || 'Job'}</span>
                      </div>
                      <a href={run.html_url || run.url} target="_blank" rel="noreferrer" className="text-blue-500 hover:text-white ml-2">[VIEW]</a>
                    </div>
                  ))}
                </div>
              </section>

              <section className="border border-amber-500 p-4 bg-amber-500/5">
                <h2 className="text-sm font-bold mb-4 flex items-center gap-2 text-amber-500">
                  <AlertCircle className="w-4 h-4" /> SYSTEM_MESSAGES
                </h2>
                <div className="text-[10px] space-y-2 opacity-80">
                  <p className="border-l-2 border-amber-500 pl-2">
                    <span className="font-bold">[SYS] </span> Webhook established for archive-zips.yml.
                  </p>
                  <p className="border-l-2 border-green-500 pl-2">
                    <span className="font-bold">[NET] </span> Success rate stabilized at {stats.successRate}%.
                  </p>
                  <p className="border-l-2 border-blue-500 pl-2">
                    <span className="font-bold">[DB] </span> Total registry entries: {tribunais.length} tribunals.
                  </p>
                  {error && (
                    <p className="border-l-2 border-red-500 pl-2 text-red-500 animate-pulse">
                      <span className="font-bold">[ERR] </span> {error}
                    </p>
                  )}
                </div>
              </section>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            <section className="border border-[#00ff41] p-4 h-full bg-[#00ff41]/5">
              <h2 className="text-sm font-bold mb-6 flex items-center gap-2">
                <Database className="w-4 h-4" /> TRIBUNAL_REGISTRY
              </h2>
              <div className="space-y-4 max-h-[600px] overflow-y-auto scrollbar-terminal pr-2">
                {tribunais.map((t) => (
                  <div key={t.tribunal} className="relative mb-4 group">
                    <div className="flex justify-between items-end mb-1">
                      <span className="text-xs font-bold">{t.tribunal}</span>
                      <span className="text-[9px] opacity-60">v1.zip</span>
                    </div>
                    <div className="w-full bg-[#00ff41]/10 h-1 mb-1">
                      <div
                        className="bg-[#00ff41] h-full"
                        style={{ width: `${Math.min((t.total_dates / 260) * 100, 100)}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[8px] opacity-40">
                      <span>{t.total_dates} DAYS_SYNCED</span>
                      <span>{formatNumber(t.total_records)} RECS</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>

        {/* Footer Bar */}
        <footer className="mt-8 flex justify-between items-center text-[9px] border-t border-[#00ff41]/20 pt-4 opacity-70">
          <div className="flex gap-4">
            <span>UPLINK: ACTIVE</span>
            <span>BANDWIDTH: 420 MB/S</span>
            <span>THREADS: 16</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 animate-pulse"></div>
            <span>TRANSMISSION_ENCRYPTED_RSA_4096</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
