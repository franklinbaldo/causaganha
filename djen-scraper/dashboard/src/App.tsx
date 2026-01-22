import { useState, useEffect } from 'react';
import { Card, Title, Text, Metric, Flex, ProgressBar, Grid, Badge, Table, TableHead, TableHeaderCell, TableBody, TableRow, TableCell, AreaChart } from '@tremor/react';

const API_BASE = 'https://djen-scraper.franklinbaldo.workers.dev';

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

interface TribunalDetail {
  tribunal: string;
  dates: {
    date: string;
    records: number;
    bytes: number;
    version: number;
    hash: string;
  }[];
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
  const [selectedTribunal, setSelectedTribunal] = useState<string | null>(null);
  const [tribunalDetail, setTribunalDetail] = useState<TribunalDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [stateRes, tribunaisRes] = await Promise.all([
          fetch(`${API_BASE}/state`),
          fetch(`${API_BASE}/api/tribunais`)
        ]);

        if (!stateRes.ok || !tribunaisRes.ok) {
          setError(`API Error: ${stateRes.status} / ${tribunaisRes.status}`);
          setLoading(false);
          return;
        }

        const stateData = await stateRes.json();
        const tribunaisData = await tribunaisRes.json();
        setState(stateData);
        setTribunais(tribunaisData.tribunais);
        setError(null);
      } catch (error) {
        console.error('Failed to fetch data:', error);
        setError(error instanceof Error ? error.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedTribunal) {
      fetch(`${API_BASE}/api/tribunal/${selectedTribunal}`)
        .then(res => res.json())
        .then(setTribunalDetail)
        .catch(console.error);
    }
  }, [selectedTribunal]);

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
          <Title className="text-white mb-4">⚠️ Cloudflare Worker API Indisponível</Title>
          <Text className="text-slate-300 mb-4">
            O dashboard precisa do Cloudflare Worker backend para funcionar.
            A API não está respondendo em: <code className="bg-slate-700 px-2 py-1 rounded">{API_BASE}</code>
          </Text>
          {error && (
            <Text className="text-red-400 mb-4">
              Erro: {error}
            </Text>
          )}
          <div className="bg-slate-900 p-4 rounded border border-slate-700">
            <Text className="text-slate-400 font-mono text-sm mb-2">Para resolver:</Text>
            <ol className="text-slate-300 text-sm space-y-2 list-decimal list-inside">
              <li>Instalar Wrangler CLI: <code className="bg-slate-700 px-2 py-1 rounded">npm install -g wrangler</code></li>
              <li>Autenticar: <code className="bg-slate-700 px-2 py-1 rounded">wrangler login</code></li>
              <li>Deploy worker: <code className="bg-slate-700 px-2 py-1 rounded">cd djen-scraper/cloudflare/worker && wrangler deploy</code></li>
            </ol>
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
            <Title className="text-white text-2xl md:text-3xl">DJEN Scraper Dashboard</Title>
            <Text className="text-slate-400">
              Última atualização: {new Date(state.stats.last_run).toLocaleString('pt-BR')}
            </Text>
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
                  className="cursor-pointer hover:bg-slate-700"
                  onClick={() => setSelectedTribunal(t.tribunal)}
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

        {/* Tribunal Detail Modal/Panel */}
        {selectedTribunal && tribunalDetail && (
          <Card className="bg-slate-800 border-slate-700 mb-8">
            <Flex justifyContent="between" alignItems="center" className="mb-4">
              <Title className="text-white">Detalhes: {selectedTribunal}</Title>
              <button
                onClick={() => setSelectedTribunal(null)}
                className="text-slate-400 hover:text-white"
              >
                Fechar
              </button>
            </Flex>

            <Text className="text-slate-400 mb-4">
              {tribunalDetail.dates.length} dias baixados
            </Text>

            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell className="text-slate-400">Data</TableHeaderCell>
                  <TableHeaderCell className="text-slate-400 text-right">Comunicações</TableHeaderCell>
                  <TableHeaderCell className="text-slate-400 text-right">Tamanho</TableHeaderCell>
                  <TableHeaderCell className="text-slate-400 text-right">Versão</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tribunalDetail.dates.map((d) => (
                  <TableRow key={d.date}>
                    <TableCell className="text-white">{d.date}</TableCell>
                    <TableCell className="text-right text-white">{formatNumber(d.records)}</TableCell>
                    <TableCell className="text-right text-white">{formatBytes(d.bytes)}</TableCell>
                    <TableCell className="text-right text-slate-300">v{d.version}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}

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
          Auto-refresh: 30s | API: {API_BASE}
        </Text>
      </div>
    </div>
  );
}
