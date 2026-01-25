import { useState, useEffect } from 'react';
import { Card, Title, Text, Metric, Flex, ProgressBar, Grid, Badge, Table, TableHead, TableHeaderCell, TableBody, TableRow, TableCell, AreaChart } from '@tremor/react';

const IA_SEARCH_URL = "https://archive.org/advancedsearch.php?q=identifier:djen-raw-*&fl[]=identifier&fl[]=date&fl[]=tribunal&fl[]=total_comunicacoes&rows=1000&output=json";

interface State {
  current: {
    date: string;
    status: string;
    tribunais_done: string[];
    tribunais_pending: string[];
    records: number;
  };
  mode: 'd1' | 'backfill';
  backfill: {
    oldest_target: string;
    completed_dates: string[];
    skipped_dates: string[];
  };
  stats: {
    total_records: number;
    total_days_archived: number;
    last_run: string;
    errors_today: number;
  };
}

interface TribunalSummary {
  tribunal: string;
  total_dates: number;
  total_records: number;
  total_bytes: number;
  oldest_date: string | null;
  newest_date: string | null;
}


function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatNumber(n: number): string {
  return n.toLocaleString('pt-BR');
}

export default function App() {
  const [state, setState] = useState<State | null>(null);
  const [tribunais, setTribunais] = useState<TribunalSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(IA_SEARCH_URL);
        if (!response.ok) {
          setError(`IA API Error: ${response.status}`);
          setLoading(false);
          return;
        }

        const data = await response.json();
        const docs = data.response.docs;

        // Process IA docs into Dashboard State
        const tribunalsMap: Record<string, TribunalSummary> = {};
        let totalRecords = 0;
        let newestDate = '2000-01-01';

        docs.forEach((doc: any) => {
          const trib = doc.tribunal || doc.identifier.split('-').pop();
          const date = (doc.date || '').split('T')[0];
          const records = parseInt(doc.total_comunicacoes || '0', 10);

          if (date > newestDate) newestDate = date;
          totalRecords += records;

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
        });

        const tribunaisArray = Object.values(tribunalsMap).sort((a, b) => b.total_records - a.total_records);

        setTribunais(tribunaisArray);
        setState({
          current: {
            date: newestDate,
            status: 'complete',
            tribunais_done: tribunaisArray.filter(t => t.newest_date === newestDate).map(t => t.tribunal),
            tribunais_pending: [],
            records: tribunaisArray.filter(t => t.newest_date === newestDate).reduce((acc, t) => acc + t.total_records, 0),
          },
          mode: 'backfill',
          backfill: {
            oldest_target: '2020-01-01',
            completed_dates: [...new Set(docs.map((d: any) => d.date?.split('T')[0]))] as string[],
            skipped_dates: [],
          },
          stats: {
            total_records: totalRecords,
            total_days_archived: data.response.numFound,
            last_run: new Date().toISOString(),
            errors_today: 0,
          },
        });

        setError(null);
      } catch (error) {
        console.error('Failed to fetch data:', error);
        setError(error instanceof Error ? error.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // 1 minute
    return () => clearInterval(interval);
  }, []);

  // Detail fetching disabled in IA mode for now
  /*
  useEffect(() => {
    if (selectedTribunal) {
      fetch(`${API_BASE}/api/tribunal/${selectedTribunal}`)
        .then(res => res.json())
        .then(setTribunalDetail)
        .catch(console.error);
    }
  }, [selectedTribunal]);
  */

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Text className="text-white text-xl mb-2">Carregando...</Text>
          <Text className="text-slate-400">Conectando ao Cloudflare Worker API</Text>
        </div>
      </div>
    );
  }

  if (error || !state) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        <Card className="bg-slate-800 border-slate-700 max-w-2xl">
          <Title className="text-white mb-4">⚠️ Erro ao Carregar Dados do Internet Archive</Title>
          <Text className="text-slate-300 mb-4">
            O dashboard não conseguiu recuperar as informações do Internet Archive.
          </Text>
          {error && (
            <Text className="text-red-400 mb-4">
              Erro: {error}
            </Text>
          )}
          <div className="bg-slate-900 p-4 rounded border border-slate-700">
            <Text className="text-slate-400 font-mono text-sm mb-2">Monitoramento:</Text>
            <Text className="text-slate-300 text-sm">
              O processo de scraping e arquivamento agora é executado via <strong>GitHub Actions</strong>.
              As coletas são enviadas diretamente para a coleção do Internet Archive.
            </Text>
          </div>
          <Text className="text-slate-500 mt-4 text-sm">
            Tentando reconectar automaticamente a cada 30 segundos...
          </Text>
        </Card>
      </div>
    );
  }

  const progress = state.current.tribunais_done.length;
  const total = progress + state.current.tribunais_pending.length;
  const pct = total > 0 ? (progress / total) * 100 : 0;

  // Calculate total bytes from tribunais
  const totalBytes = tribunais.reduce((acc, t) => acc + t.total_bytes, 0);

  // Prepare chart data for tribunais by size
  const chartData = tribunais
    .filter(t => t.total_bytes > 0)
    .slice(0, 15)
    .map(t => ({
      name: t.tribunal,
      'Tamanho (MB)': Math.round(t.total_bytes / 1024 / 1024),
      'Comunicações': t.total_records,
    }));

  return (
    <div className="min-h-screen bg-slate-900 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        <Flex justifyContent="between" alignItems="center" className="mb-8">
          <div>
            <Title className="text-white text-2xl md:text-3xl">CausaGanha Scraper Status</Title>
            Baseado em GitHub Actions + Internet Archive
          </div>
          <Badge color={state.mode === 'd1' ? 'red' : 'blue'} size="lg">
            {state.mode === 'd1' ? 'D-1 (Ontem)' : 'Backfill'}
          </Badge>
        </Flex>

        {/* Stats Cards */}
        <Grid numItemsSm={2} numItemsLg={4} className="gap-4 mb-8">
          <Card className="bg-slate-800 border-slate-700">
            <Text className="text-slate-400">Data Atual</Text>
            <Metric className="text-white">{state.current.date}</Metric>
            <Text className="text-slate-500">
              {state.current.status === 'complete' ? 'Completo' : 'Em progresso'}
            </Text>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <Text className="text-slate-400">Progresso do Dia</Text>
            <Metric className="text-white">{progress}/{total}</Metric>
            <ProgressBar value={pct} color="blue" className="mt-2" />
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <Text className="text-slate-400">Total de Comunicações</Text>
            <Metric className="text-emerald-400">{formatNumber(state.stats.total_records)}</Metric>
            <Text className="text-slate-500">{formatNumber(state.current.records)} hoje</Text>
          </Card>

          <Card className="bg-slate-800 border-slate-700">
            <Text className="text-slate-400">Armazenamento</Text>
            <Metric className="text-white">{formatBytes(totalBytes)}</Metric>
            <Text className="text-slate-500">{tribunais.filter(t => t.total_dates > 0).length} tribunais</Text>
          </Card>
        </Grid>

        {/* Backfill Progress */}
        <Card className="bg-slate-800 border-slate-700 mb-8">
          <Title className="text-white mb-4">Progresso do Backfill</Title>
          <Grid numItemsSm={3} className="gap-4">
            <div>
              <Text className="text-slate-400">Dias Completos</Text>
              <Metric className="text-white">{state.backfill.completed_dates.length}</Metric>
            </div>
            <div>
              <Text className="text-slate-400">Dias Pulados</Text>
              <Metric className="text-white">{state.backfill.skipped_dates.length}</Metric>
            </div>
            <div>
              <Text className="text-slate-400">Alvo Mais Antigo</Text>
              <Metric className="text-white">{state.backfill.oldest_target}</Metric>
            </div>
          </Grid>
        </Card>

        {/* Chart - Top Tribunais */}
        {chartData.length > 0 && (
          <Card className="bg-slate-800 border-slate-700 mb-8">
            <Title className="text-white mb-4">Top 15 Tribunais por Tamanho</Title>
            <AreaChart
              className="h-72"
              data={chartData}
              index="name"
              categories={['Tamanho (MB)']}
              colors={['blue']}
              showLegend={false}
              showGridLines={false}
            />
          </Card>
        )}

        {/* Tribunais Table */}
        <Card className="bg-slate-800 border-slate-700 mb-8">
          <Title className="text-white mb-4">Tribunais</Title>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeaderCell className="text-slate-400">Tribunal</TableHeaderCell>
                <TableHeaderCell className="text-slate-400 text-right">Dias</TableHeaderCell>
                <TableHeaderCell className="text-slate-400 text-right">Comunicações</TableHeaderCell>
                <TableHeaderCell className="text-slate-400 text-right">Tamanho</TableHeaderCell>
                <TableHeaderCell className="text-slate-400">Mais Antigo</TableHeaderCell>
                <TableHeaderCell className="text-slate-400">Mais Recente</TableHeaderCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tribunais.map((t) => (
                <TableRow
                  key={t.tribunal}
                  className="hover:bg-slate-700"
                >
                  <TableCell>
                    <Badge color={t.total_dates > 0 ? 'emerald' : 'gray'}>
                      {t.tribunal}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-white">{t.total_dates}</TableCell>
                  <TableCell className="text-right text-white">{formatNumber(t.total_records)}</TableCell>
                  <TableCell className="text-right text-white">{formatBytes(t.total_bytes)}</TableCell>
                  <TableCell className="text-slate-300">{t.oldest_date || '-'}</TableCell>
                  <TableCell className="text-slate-300">{t.newest_date || '-'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>


        {/* Current Day Tribunais Status */}
        <Card className="bg-slate-800 border-slate-700">
          <Title className="text-white mb-4">Tribunais - {state.current.date}</Title>
          <div className="flex flex-wrap gap-2">
            {state.current.tribunais_done.map(t => (
              <Badge key={t} color="emerald" size="sm">{t}</Badge>
            ))}
            {state.current.tribunais_pending.map(t => (
              <Badge key={t} color="gray" size="sm">{t}</Badge>
            ))}
          </div>
        </Card>

        <Text className="text-center text-slate-500 mt-8">
          Auto-refresh: 60s | Fonte: Internet Archive (Advanced Search)
        </Text>
      </div>
    </div>
  );
}
