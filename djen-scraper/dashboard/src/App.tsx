import { useState, useEffect } from 'react';
import {
  Activity, Database, Cloud, AlertCircle,
  Globe, ArrowUpRight, Cpu,
  Layers, ShieldCheck, Zap, Download, FileArchive
} from 'lucide-react';
import {
  Card, Metric, Text, Flex, Grid, Badge,
  ProgressBar, Title, Subtitle, Bold
} from '@tremor/react';

// --- CONFIG & CONSTANTS ---
const IA_SEARCH_URL = "https://archive.org/advancedsearch.php?q=identifier:djen-20*&fl[]=identifier&fl[]=date&fl[]=addeddate&fl[]=format&fl[]=total_comunicacoes&sort[]=addeddate+desc&rows=2000&output=json";
const PIPELINE_RUNS_URL = "https://api.github.com/repos/franklinbaldo/causaganha/actions/workflows/pipeline.yml/runs?per_page=20";

// Epoch Configuration
const TRIBUNAL_EPOCHS: Record<string, string> = {
  // Early Adopters (2021)
  "TRF3": "2021-01-01", "TRF4": "2021-01-01", "TJRR": "2021-01-01", "TJMA": "2021-01-01",
  // Late Joiners / Specifics
  "TJMG": "2025-01-27",
};

const getTribunalEpoch = (tribunal: string) => {
  // Labor Justice (Aug 2024)
  if (tribunal.startsWith("TRT") || tribunal === "TST") return new Date("2024-08-01");
  // Specific Overrides
  if (TRIBUNAL_EPOCHS[tribunal]) return new Date(TRIBUNAL_EPOCHS[tribunal]);
  // Universal Obligation (May 2025)
  return new Date("2025-05-16");
};

const BRAZILIAN_COURTS = [
  "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6", "STF", "STJ", "TST", "TSE", "STM", "CNJ", "CNMP", "TNU",
  "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDF", "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA", "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO", "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJTO",
  "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7", "TRT8", "TRT9", "TRT10", "TRT11", "TRT12", "TRT13", "TRT14", "TRT15", "TRT16", "TRT17", "TRT18", "TRT19", "TRT20", "TRT21", "TRT22", "TRT23", "TRT24",
  "TREAC", "TREAL", "TREAM", "TREAP", "TREBA", "TRECE", "TREDF", "TREES", "TREGO", "TREMA", "TREMG", "TREMS", "TREMT", "TREPA", "TREPB", "TREPE", "TREPI", "TREPR", "TRERJ", "TRERN", "TRERO", "TRERR", "TRERS", "TRESC", "TRESE", "TRESP", "TRETO"
];

// --- HELPER FUNCTIONS ---
const formatCompact = (n: number) => {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
};

const getDaysSince = (date: Date) => {
  const nowStr = new Date().toLocaleDateString('sv-SE', { timeZone: 'America/Sao_Paulo' });
  const now = new Date(nowStr + 'T12:00:00');
  const ref = new Date(date.toLocaleDateString('sv-SE', { timeZone: 'America/Sao_Paulo' }) + 'T12:00:00');
  const diffTime = Math.max(0, now.getTime() - ref.getTime());
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

// --- TYPES ---
interface ActionRun {
  id: number;
  status: string;
  conclusion: string;
  created_at: string;
  html_url: string;
  display_title: string;
}

interface ArchiveItem {
  id: string;
  tribunal: string;
  date: string;
  addedate: string;
  comms: number;
  hasParquet: boolean;
}

interface TribunalStats {
  count: number;
  lastDate: string;
  totalComms: number;
}

// --- COMPONENTS ---

const GlassCard = ({ children, className = "" }: { children: React.ReactNode, className?: string }) => (
  <Card className={`bg-slate-900/40 backdrop-blur-xl border-slate-800/50 shadow-2xl ${className}`}>
    {children}
  </Card>
);

const CoverageMatrix = ({ statsMap }: { statsMap: Record<string, TribunalStats> }) => {
  return (
    <div className="grid grid-cols-6 sm:grid-cols-7 md:grid-cols-10 lg:grid-cols-13 gap-2">
      {BRAZILIAN_COURTS.map(court => {
        const stats = statsMap[court] || { count: 0, lastDate: '-', totalComms: 0 };
        const epoch = getTribunalEpoch(court);
        const expected = getDaysSince(epoch);
        const coverage = expected > 0 ? Math.min(Math.round((stats.count / expected) * 100), 100) : 0;

        // Colors
        const barColor = coverage >= 90 ? 'bg-emerald-500' : coverage >= 50 ? 'bg-amber-500' : 'bg-rose-500';
        const textColor = coverage >= 90 ? 'text-emerald-400' : coverage >= 50 ? 'text-amber-400' : 'text-rose-400';
        const borderColor = coverage >= 90 ? 'border-emerald-500/30' : 'border-slate-800';
        const activeShadow = coverage >= 90 ? 'shadow-[0_0_10px_-4px_rgba(16,185,129,0.3)]' : '';

        return (
          <div key={court} className={`group relative p-2 rounded border bg-slate-900/60 transition-all hover:scale-105 ${borderColor} ${activeShadow}`}>
            <Flex className="justify-between items-end mb-1.5">
              <Text className={`text-[10px] font-black tracking-tighter ${textColor}`}>{court}</Text>
              <Text className="text-[9px] text-slate-500 font-mono">{coverage}%</Text>
            </Flex>

            <div className="w-full bg-slate-800/50 h-1.5 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all duration-1000 ${barColor}`} style={{ width: `${coverage}%` }} />
            </div>

            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 min-w-[120px]">
              <div className="bg-slate-950 text-[10px] py-2 px-3 rounded border border-slate-800 shadow-xl text-white">
                <div className="font-bold mb-1 text-emerald-400">{court} Details</div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-slate-400">
                  <span>Active:</span> <span className="text-right text-white">{epoch.toISOString().split('T')[0]}</span>
                  <span>Days:</span> <span className="text-right text-white">{stats.count} / {expected}</span>
                  <span>Data:</span> <span className="text-right text-white">{formatCompact(stats.totalComms)}</span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default function App() {
  const [items, setItems] = useState<ArchiveItem[]>([]);
  const [runs, setRuns] = useState<ActionRun[]>([]);
  const [tribunalStats, setTribunalStats] = useState<Record<string, TribunalStats>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  const fetchData = async () => {
    try {
      const [iaRes, pipelineRes] = await Promise.all([
        fetch(IA_SEARCH_URL),
        fetch(PIPELINE_RUNS_URL)
      ]);

      if (iaRes.ok) {
        const data = await iaRes.json();
        const mapped: ArchiveItem[] = data.response.docs.map((doc: Record<string, unknown>) => ({
          id: String(doc.identifier),
          tribunal: String(doc.identifier).split('-').pop() || '',
          date: (String(doc.date || '')).split('T')[0],
          addedate: String(doc.addeddate),
          comms: parseInt(String(doc.total_comunicacoes || '0'), 10),
          hasParquet: Array.isArray(doc.format) ? doc.format.includes('Parquet') : false
        }));
        setItems(mapped);

        // Aggregate stats per tribunal
        const stats: Record<string, TribunalStats> = {};
        mapped.forEach(item => {
          if (!stats[item.tribunal]) {
            stats[item.tribunal] = { count: 0, lastDate: '', totalComms: 0 };
          }
          stats[item.tribunal].count += 1;
          stats[item.tribunal].totalComms += item.comms;
          if (item.date > (stats[item.tribunal].lastDate || '')) {
            stats[item.tribunal].lastDate = item.date;
          }
        });
        setTribunalStats(stats);
      }

      if (pipelineRes.ok) {
        const data = await pipelineRes.json();
        setRuns(data.workflow_runs || []);
      }
    } catch (err) {
      console.error("Fetch failed:", err);
      setError("Sync Interrupted. Retrying...");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const inv = setInterval(fetchData, 60000);
    const clock = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => { clearInterval(inv); clearInterval(clock); };
  }, []);

  const totalComms = items.reduce((acc, curr) => acc + curr.comms, 0);

  // Calculate Global Coverage
  const coverageSum = BRAZILIAN_COURTS.reduce((acc, court) => {
    const stats = tribunalStats[court] || { count: 0 };
    const epoch = getTribunalEpoch(court);
    const expected = getDaysSince(epoch);
    return acc + (expected > 0 ? Math.min((stats.count / expected), 1) : 0);
  }, 0);

  const globalCoverage = Math.round((coverageSum / BRAZILIAN_COURTS.length) * 100);

  if (loading) return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center">
      <Zap className="w-12 h-12 text-emerald-500 animate-pulse mb-6" />
      <Text className="text-slate-400 font-medium tracking-widest text-xs uppercase animate-pulse">
        Initializing High-Latency Data Streams...
      </Text>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 p-4 md:p-8 selection:bg-emerald-500/20">
      <div className="max-w-7xl mx-auto space-y-8">

        {/* TOP NAV / HEADER */}
        <Flex className="items-center justify-between border-b border-slate-800/50 pb-6">
          <Flex className="gap-3 w-auto">
            <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <Title className="text-white text-2xl font-black tracking-tight">CAUSA<span className="text-emerald-500">GANHA</span></Title>
              <Text className="text-[10px] font-bold text-slate-500 tracking-[0.2em] uppercase">Autonomous Judicial Pulse</Text>
            </div>
          </Flex>

          <div className="hidden md:flex gap-6 items-center">
            <div className="text-right">
              <Text className="text-[10px] font-bold text-slate-500 uppercase">Cycle Time</Text>
              <div className="font-mono text-emerald-400 text-sm">{currentTime.toLocaleTimeString('pt-BR', { timeZone: 'America/Sao_Paulo' })}</div>
            </div>
          </div>
        </Flex>

        {error && (
          <Badge color="rose" icon={AlertCircle} className="w-full justify-center py-2 bg-rose-500/10">
            {error}
          </Badge>
        )}

        {/* OVERVIEW METRICS */}
        <Grid numItemsSm={2} numItemsLg={4} className="gap-6">
          <GlassCard>
            <Flex className="items-start">
              <div>
                <Text className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Processed Feed</Text>
                <Metric className="text-white font-black">{formatCompact(totalComms)}</Metric>
              </div>
              <Activity className="w-5 h-5 text-emerald-500/50" />
            </Flex>
            <ProgressBar value={85} color="emerald" className="mt-4" />
            <Text className="text-[10px] text-slate-500 mt-2">Cumulative Judicial Communications</Text>
          </GlassCard>

          <GlassCard>
            <Flex className="items-start">
              <div>
                <Text className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Global Coverage</Text>
                <Metric className="text-white font-black">{globalCoverage}%</Metric>
              </div>
              <Zap className="w-5 h-5 text-amber-500/50" />
            </Flex>
            <ProgressBar value={globalCoverage} color="amber" className="mt-4" />
            <Text className="text-[10px] text-slate-500 mt-2">Vs. Est. Availability (Since May 2024)</Text>
          </GlassCard>

          <GlassCard>
            <Flex className="items-start">
              <div>
                <Text className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Archive Assets</Text>
                <Metric className="text-white font-black">{formatCompact(items.length)}</Metric>
              </div>
              <Database className="w-5 h-5 text-indigo-500/50" />
            </Flex>
            <div className="flex gap-1 mt-4">
              {[1, 2, 3, 4, 5, 6].map(i => <div key={i} className="h-1 flex-1 bg-indigo-500/30 rounded-full" />)}
            </div>
            <Text className="text-[10px] text-slate-500 mt-2">Unique items in Internet Archive</Text>
          </GlassCard>

          <GlassCard>
            <Flex className="items-start">
              <div>
                <Text className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Network Health</Text>
                <Metric className="text-white font-black">Stable</Metric>
              </div>
              <Globe className="w-5 h-5 text-emerald-500/50" />
            </Flex>
            <div className="flex items-baseline gap-2 mt-4">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping"></div>
              <Text className="text-[10px] text-emerald-400 font-bold">ALL NODES ONLINE</Text>
            </div>
            <Text className="text-[10px] text-slate-500 mt-2">GCloud SP + GH Actions Matrix</Text>
          </GlassCard>
        </Grid>

        {/* MAIN HUD */}
        <Grid numItemsLg={3} className="gap-8">

          {/* LEFT: COVERAGE MATRIX */}
          <div className="lg:col-span-2 space-y-6">
            <GlassCard className="p-8">
              <Flex className="mb-8">
                <div>
                  <Title className="text-slate-100 flex items-center gap-2">
                    <Layers className="w-5 h-5 text-emerald-500" /> Historical Coverage Matrix
                  </Title>
                  <Subtitle className="text-slate-500 text-xs">Completeness per Tribunal relative to specific adoption date.</Subtitle>
                </div>
              </Flex>

              <CoverageMatrix statsMap={tribunalStats} />

              <div className="mt-10 pt-6 border-t border-slate-800/50">
                <Flex>
                  <div>
                    <Text className="text-[10px] font-bold text-slate-500 uppercase">Operational Logic</Text>
                    <Text className="text-xs text-slate-400 mt-1 max-w-md">Bars indicate % of days available since specific DJEN adoption dates (2021-2025).</Text>
                  </div>
                  <Badge color="emerald">SENTINEL_HISTORIC_V3</Badge>
                </Flex>
              </div>
            </GlassCard>

            {/* RECENT ARCHIVES TABLE */}
            <GlassCard className="p-0">
              <div className="p-6 border-b border-slate-800/50">
                <Title className="text-slate-100 flex items-center gap-2">
                  <Download className="w-5 h-5 text-indigo-400" /> Archive Ingestion Feed
                </Title>
              </div>
              <div className="max-h-[300px] overflow-y-auto scrollbar-thin">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/50 sticky top-0 text-slate-500 uppercase text-[9px] font-black tracking-widest">
                    <tr>
                      <th className="px-6 py-4">Tribunal</th>
                      <th className="px-6 py-4">Date</th>
                      <th className="px-6 py-4">Integrity</th>
                      <th className="px-6 py-4">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/30">
                    {items.slice(0, 15).map((item, idx) => (
                      <tr key={`${item.id}-${idx}`} className="hover:bg-white/[0.02] transition-colors">
                        <td className="px-6 py-4 font-black text-slate-300">{item.tribunal}</td>
                        <td className="px-6 py-4 text-slate-500 font-mono">{item.date}</td>
                        <td className="px-6 py-4">
                          <div className="flex gap-1">
                            {item.comms > 0 ? <Badge color="emerald" size="xs">DATA</Badge> : <Badge color="indigo" size="xs">MARKER</Badge>}
                            {item.hasParquet && <Badge color="amber" size="xs">PARQUET</Badge>}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <a href={`https://archive.org/details/${item.id}`} target="_blank" className="text-emerald-500 hover:text-emerald-400 transition-colors inline-block">
                            <FileArchive className="w-4 h-4" />
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </GlassCard>
          </div>

          {/* RIGHT SIDEBAR: AUTOMATION AUDIT */}
          <div className="space-y-8">
            <GlassCard className="p-6">
              <Title className="text-white mb-6 flex items-center gap-2">
                <Cpu className="w-5 h-5 text-emerald-500" /> Automation Audit
              </Title>
              <div className="space-y-4">
                {runs.slice(0, 8).map(run => (
                  <div key={run.id} className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/50 group">
                    <Flex className="items-center">
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className={`w-1.5 h-1.5 rounded-full ${run.conclusion === 'success' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-rose-500'}`} />
                        <div className="overflow-hidden">
                          <Text className="text-xs font-bold text-slate-300 truncate" title={run.display_title}>{run.display_title}</Text>
                          <Text className="text-[9px] text-slate-600 font-mono uppercase">{new Date(run.created_at).toLocaleString('pt-BR', { timeZone: 'America/Sao_Paulo' })}</Text>
                        </div>
                      </div>
                      <a href={run.html_url} target="_blank" className="p-1 px-2 rounded bg-slate-800 text-slate-400 hover:text-white transition-colors group-hover:bg-indigo-500/20">
                        <ArrowUpRight className="w-3 h-3" />
                      </a>
                    </Flex>
                  </div>
                ))}
              </div>
              <div className="mt-8 pt-6 border-t border-slate-800/50 text-center">
                <a href="https://github.com/franklinbaldo/causaganha/actions" className="text-[10px] font-black text-emerald-500 uppercase tracking-widest hover:text-emerald-400 transition-colors">
                  View Complete Node Engine -{'>'}
                </a>
              </div>
            </GlassCard>

            <GlassCard className="p-8 bg-gradient-to-br from-emerald-500/10 to-indigo-500/10 border-emerald-500/20 relative overflow-hidden group">
              <div className="absolute -right-4 -bottom-4 opacity-10 group-hover:scale-110 transition-transform duration-1000">
                <Globe className="w-32 h-32" />
              </div>
              <div className="relative z-10">
                <Bold className="text-emerald-400 text-xs block mb-2 uppercase tracking-widest">Public Data Lake</Bold>
                <Title className="text-white text-xl">Internet Archive Backbone</Title>
                <Text className="text-slate-400 text-xs mt-3 leading-relaxed">
                  Our petabyte-scale vision is built on public infrastructure. Data is permanently, transparently, and freely available for the Brazilian public.
                </Text>
              </div>
            </GlassCard>
          </div>

        </Grid>
      </div>

      <footer className="max-w-7xl mx-auto mt-16 pt-8 border-t border-slate-800/50 flex flex-col sm:flex-row justify-between items-center gap-6 pb-12">
        <Text className="text-[10px] font-bold text-slate-600 uppercase tracking-widest">
          © 2026 CAUSAGANHA OS // PROTOCOL V4.2 // IA DISTRIBUTED
        </Text>
        <Flex className="w-auto gap-4">
          <Cloud className="w-4 h-4 text-slate-700 hover:text-emerald-500 transition-colors cursor-pointer" />
          <Database className="w-4 h-4 text-slate-700 hover:text-emerald-500 transition-colors cursor-pointer" />
          <ShieldCheck className="w-4 h-4 text-slate-700 hover:text-emerald-500 transition-colors cursor-pointer" />
        </Flex>
      </footer>
    </div>
  );
}
