import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Activity, Database, Cloud, AlertCircle, CheckCircle2,
  Cpu, Globe, ArrowUpRight, Info, FileText, FileArchive,
  BarChart3, RefreshCw, Layers
} from 'lucide-react';

const IA_SEARCH_URL = "https://archive.org/advancedsearch.php?q=(identifier:djen-raw-*) OR (identifier:djen-parquet-*)&fl[]=identifier&fl[]=date&fl[]=tribunal&fl[]=total_comunicacoes&fl[]=addeddate&sort[]=addeddate+desc&rows=1000&output=json";
const GITHUB_RUNS_URL = "https://api.github.com/repos/franklinbaldo/causaganha/actions/runs?workflow_id=archive-zips.yml&per_page=15";
const LOCAL_RUNS_URL = "/causaganha/run_stats.json";

interface ActionRun {
  id: number;
  status: string;
  conclusion: string;
  createdAt: string;
  displayTitle?: string;
  display_title?: string;
  name?: string;
  workflowName?: string;
  html_url: string;
  url?: string;
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
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    totalRecords: 0,
    totalItems: 0,
    progress: '0',
    successRate: '0',
    newestDate: 'N/A'
  });

  const fetchData = async () => {
    try {
      const [iaRes, runsRes] = await Promise.all([
        fetch(IA_SEARCH_URL).catch(() => null),
        fetch(GITHUB_RUNS_URL).catch(() => null)
      ]);

      if (iaRes && iaRes.ok) {
        const iaDataJson = await iaRes.json();
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
          if (isParquet) archiveFeedMap[feedKey].parquetId = doc.identifier;
          else archiveFeedMap[feedKey].zipId = doc.identifier;
        });

        setTribunais(Object.values(tribunalsMap).sort((a, b) => b.total_records - a.total_records));
        const sortedFeed = Object.values(archiveFeedMap).sort((a, b) =>
          new Date(b.addeddate).getTime() - new Date(a.addeddate).getTime()
        );
        setRecentArchives(sortedFeed.slice(0, 15));

        const totalTarget = 91 * 260 * 4;
        const progressPct = Math.min(((iaDataJson.response.numFound / totalTarget) * 100), 100).toFixed(1);

        setStats(prev => ({
          ...prev,
          totalRecords,
          totalItems: iaDataJson.response.numFound,
          progress: progressPct,
          newestDate: newestDate
        }));
        setError(null);
      } else {
        setError("Internet Archive API Indisponível");
      }

      if (runsRes && runsRes.ok) {
        const runsData = await runsRes.json();
        const workflowRuns = runsData.workflow_runs || [];
        setRuns(workflowRuns);
        const successCount = workflowRuns.filter((r: any) => r.conclusion === 'success').length;
        const rate = ((successCount / Math.max(workflowRuns.length, 1)) * 100).toFixed(0);
        setStats(prev => ({ ...prev, successRate: rate }));
      } else {
        const localRes = await fetch(LOCAL_RUNS_URL).catch(() => null);
        if (localRes && localRes.ok) setRuns(await localRes.json());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Falha no sistema');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <RefreshCw className="w-10 h-10 text-indigo-600 animate-spin mb-4" />
        <p className="text-slate-600 font-medium italic">Sincronizando infraestrutura de dados...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-100 selection:text-indigo-900 leading-normal">
      {/* Top Navigation Bar */}
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-3">
              <div className="bg-indigo-600 p-2 rounded-lg">
                <Layers className="text-white w-5 h-5" />
              </div>
              <span className="text-xl font-bold tracking-tight text-slate-900">CausaGanha <span className="text-indigo-600">Console</span></span>
            </div>
            <div className="flex items-center gap-4 text-xs font-medium text-slate-500 bg-slate-100 px-3 py-1.5 rounded-full">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              SISTEMA OPERACIONAL // {new Date().toLocaleTimeString()}
            </div>
          </div>
        </div>
      </nav>

      {error && (
        <div className="bg-red-50 border-b border-red-100 py-3">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center gap-3 text-red-700 text-sm font-bold">
            <AlertCircle className="w-4 h-4" />
            ATENÇÃO: {error}. Alguns dados podem estar desatualizados.
          </div>
        </div>
      )}

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Intro Section */}
        <header className="mb-10 max-w-3xl">
          <h1 className="text-3xl font-extrabold text-slate-900 mb-4 tracking-tight">Monitoramento de Extração de Dados</h1>
          <p className="text-slate-600 leading-relaxed text-lg">
            Acompanhe em tempo real o processo de captura e estruturação de diários da justiça do DJEN.
            Nossa infraestrutura automatizada realiza o scraping, validação e arquivamento permanente dos dados para análise preditiva de performance jurídica.
          </p>
        </header>

        {/* Global KPIs Container */}
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-indigo-600" />
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">Métricas Principais de Operação</h2>
            <div className="group relative">
              <Info className="w-4 h-4 text-slate-400 cursor-help" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-2 bg-slate-800 text-white text-[10px] rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 leading-tight">
                Estas métricas representam a saúde e o volume total de dados processados desde o início do projeto.
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-6">
            {[
              { label: 'Total Comunicados', val: formatNumber(stats.totalRecords), info: 'Volume acumulado de atos jurídicos processados.', icon: Activity },
              { label: 'Itens Arquivados', val: stats.totalItems, info: 'Quantidade de pacotes (ZIP/Parquet) no Internet Archive.', icon: Database },
              { label: 'Cobertura Histórica', val: `${stats.progress}%`, info: 'Progresso estimado vs meta de 4 anos de dados históricos.', icon: Globe },
              { label: 'Saúde das Runs', val: `${stats.successRate}%`, info: 'Taxa de sucesso dos últimos 15 processos automáticos.', icon: CheckCircle2 },
              { label: 'Dados Recentes', val: stats.newestDate, info: 'Data do caderno mais recente processado com sucesso.', icon: RefreshCw }
            ].map((kpi, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
                    <kpi.icon className="w-5 h-5" />
                  </div>
                  <div className="group relative">
                    <Info className="w-3.5 h-3.5 text-slate-300 cursor-help" />
                    <div className="absolute bottom-full right-0 mb-2 w-48 p-2 bg-slate-800 text-white text-[10px] rounded shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20">
                      {kpi.info}
                    </div>
                  </div>
                </div>
                <div className="text-2xl font-bold text-slate-900 mb-1">{kpi.val}</div>
                <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{kpi.label}</div>
              </motion.div>
            ))}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
            <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
              <div className="p-6 border-b border-slate-100 flex justify-between items-center">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Últimos Arquivos Processados</h3>
                  <p className="text-sm text-slate-500 mt-1">Dados brutos (ZIP) e estruturados (PARQUET) disponíveis no Internet Archive.</p>
                </div>
                <Cloud className="text-indigo-400 w-6 h-6" />
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
                    <tr>
                      <th className="px-6 py-4">Tribunal</th>
                      <th className="px-6 py-4">Data do Caderno</th>
                      <th className="px-6 py-4">Comunicados</th>
                      <th className="px-6 py-4">Formatos</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {recentArchives.map((doc, idx) => (
                      <tr key={idx} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4">
                          <span className="font-bold text-slate-700">{doc.tribunal}</span>
                        </td>
                        <td className="px-6 py-4 text-slate-600 font-medium">{doc.date}</td>
                        <td className="px-6 py-4 text-slate-600">{formatNumber(parseInt(doc.comms || '0'))}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            {doc.zipId && (
                              <a
                                href={`https://archive.org/details/${doc.zipId}`}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center gap-1.5 text-indigo-600 hover:text-indigo-800 font-semibold text-xs group"
                              >
                                <FileArchive className="w-3 h-3 group-hover:scale-110 transition-transform" />
                                <span className="bg-indigo-100 p-1 rounded px-1.5 py-0.5">ZIP</span>
                              </a>
                            )}
                            {doc.parquetId && (
                              <a
                                href={`https://archive.org/details/${doc.parquetId}`}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center gap-1.5 text-emerald-600 hover:text-emerald-800 font-semibold text-xs group"
                              >
                                <FileText className="w-3 h-3 group-hover:scale-110 transition-transform" />
                                <span className="bg-emerald-100 p-1 rounded px-1.5 py-0.5">PARQUET</span>
                              </a>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">Auditoria de Automação</h3>
                  <p className="text-sm text-slate-500">Histórico de execuções do robô via GitHub Actions.</p>
                </div>
                <Cpu className="text-slate-300 w-6 h-6" />
              </div>
              <div className="space-y-3">
                {runs.slice(0, 8).map((run) => (
                  <div key={run.id} className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className={`p-1.5 rounded-full ${run.conclusion === 'success' ? 'bg-emerald-100 text-emerald-600' :
                          run.status === 'in_progress' ? 'bg-amber-100 text-amber-600 animate-pulse' :
                            'bg-red-100 text-red-600'
                        }`}>
                        {run.conclusion === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-slate-700 truncate">
                          {run.display_title || run.displayTitle || run.name || 'Operação de Dados'}
                        </p>
                        <p className="text-[10px] text-slate-400 font-medium uppercase tracking-tight">{new Date(run.createdAt).toLocaleString('pt-BR')}</p>
                      </div>
                    </div>
                    <a href={run.html_url} target="_blank" rel="noreferrer" className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 flex-shrink-0">
                      INFO <ArrowUpRight className="w-3 h-3" />
                    </a>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <div className="space-y-8">
            <section className="bg-slate-900 rounded-2xl p-6 text-white shadow-xl">
              <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-400" /> Registro por Tribunal
              </h3>
              <div className="space-y-5 max-h-[700px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-700 pr-2">
                {tribunais.map((t) => (
                  <div key={t.tribunal} className="border-b border-white/5 pb-4 last:border-0">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold text-sm tracking-tight">{t.tribunal}</span>
                      <span className="text-[10px] font-black bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded uppercase tracking-widest">{t.total_dates} Dias</span>
                    </div>
                    <div className="w-full bg-white/5 h-1 rounded-full mb-2 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min((t.total_dates / 260) * 100, 100)}%` }}
                        className="bg-indigo-50 h-full rounded-full"
                      ></motion.div>
                    </div>
                    <div className="flex justify-between items-end text-[10px] text-slate-400">
                      <span>SINCRONIA: {t.oldest_date?.split('-')[0]} - {t.newest_date?.split('-')[0]}</span>
                      <span className="font-bold text-white uppercase">{formatNumber(t.total_records)} Atos</span>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-indigo-600 rounded-2xl p-6 text-white shadow-lg relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500 to-indigo-700 group-hover:scale-105 transition-transform duration-500"></div>
              <div className="relative z-10">
                <h4 className="font-bold text-lg mb-2 flex items-center gap-2">
                  <Globe className="w-5 h-5" /> Acervo Público
                </h4>
                <p className="text-indigo-100 text-sm leading-relaxed mb-4">
                  Todos os dados são persistidos no Internet Archive sob licença aberta, garantindo transparência infinita.
                </p>
                <div className="flex gap-4 text-[10px] font-bold uppercase tracking-widest">
                  <div className="bg-white/10 p-2 rounded text-center flex-1">
                    Uplink Live
                  </div>
                  <div className="bg-white/10 p-2 rounded text-center flex-1">
                    Permanent Storage
                  </div>
                </div>
              </div>
            </section>
          </div>
        </div>
      </main>

      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 border-t border-slate-200 mt-12 flex flex-col sm:flex-row justify-between items-center gap-6">
        <div className="text-slate-500 text-[11px] font-medium text-center sm:text-left">
          © 2026 Plataforma CausaGanha. Monitoramento de Infraestrutura Crítica.
          <span className="block mt-1 opacity-60 italic text-[10px]">Tecnologias: Vite + React + Lucide + Framer + Internet Archive Open API.</span>
        </div>
        <div className="flex gap-6">
          <Globe className="w-4 h-4 text-slate-400" />
          <Database className="w-4 h-4 text-slate-400" />
          <Cloud className="w-4 h-4 text-slate-400" />
        </div>
      </footer>
    </div>
  );
}
