export type CoverageFilter = 'all' | 'failed' | 'complete' | 'no-data';

export interface CompletedCatalogDay {
  tribunal_count?: number;
  absent_count?: number;
  tribunais_coletados?: string[];
  tribunais_ausentes?: string[];
  latencies?: Record<string, number>;
}

export interface CoverageDaySummary {
  key: string;
  date: string;
  collected: number;
  absent: number;
  total: number;
  pct: number;
  status: 'complete' | 'failed' | 'no-data';
  missingTribunals: string[];
}

export interface AttentionCard {
  id: string;
  tone: 'info' | 'success' | 'warning' | 'error';
  icon: string;
  title: string;
  summary: string;
  impact: string;
  cause: string;
  action: string;
}

export function summarizeCatalogDay(key: string, item: CompletedCatalogDay | undefined): CoverageDaySummary {
  const collectedList = item?.tribunais_coletados || [];
  const absentList = item?.tribunais_ausentes || [];
  const collected = item?.tribunal_count ?? collectedList.length;
  const absent = item?.absent_count ?? absentList.length;
  const total = collected + absent;
  const pct = total > 0 ? Math.min(100, (collected / total) * 100) : 0;
  return {
    key,
    date: key.replace('djen-', ''),
    collected,
    absent,
    total,
    pct,
    status: total === 0 ? 'no-data' : absent > 0 || pct < 100 ? 'failed' : 'complete',
    missingTribunals: absentList,
  };
}

export function filterCoverageDays(days: CoverageDaySummary[], filter: CoverageFilter): CoverageDaySummary[] {
  if (filter === 'all') return days;
  return days.filter(day => day.status === filter);
}

export function countCoverageFilters(days: CoverageDaySummary[]) {
  return {
    all: days.length,
    failed: days.filter(day => day.status === 'failed').length,
    complete: days.filter(day => day.status === 'complete').length,
    noData: days.filter(day => day.status === 'no-data').length,
  };
}

export function getDayStatusLabel(day: CoverageDaySummary): string {
  if (day.status === 'complete') return '✓ Completo';
  if (day.status === 'no-data') return '○ Sem dados';
  return `⚠ Falha (${day.absent} ausente${day.absent === 1 ? '' : 's'})`;
}

export function buildCatalogAttentionCards(days: CoverageDaySummary[]): AttentionCard[] {
  const cards: AttentionCard[] = [];
  const daysWithData = days.filter(day => day.total > 0).sort((a, b) => a.date.localeCompare(b.date));
  const noDataDays = days.filter(day => day.status === 'no-data');
  const lowCoverageDays = daysWithData.filter(day => day.pct < 95);

  if (lowCoverageDays.length > 0) {
    const worst = [...lowCoverageDays].sort((a, b) => a.pct - b.pct)[0];
    cards.push({
      id: 'low-coverage',
      tone: worst.pct < 80 ? 'error' : 'warning',
      icon: '⚠',
      title: 'Dias com baixa cobertura',
      summary: `${lowCoverageDays.length} dia${lowCoverageDays.length === 1 ? '' : 's'} abaixo de 95%; pior caso ${worst.date} com ${worst.pct.toFixed(1)}%.`,
      impact: 'Impacto: buscas e métricas podem omitir publicações desses tribunais.',
      cause: 'Possível causa: ZIP indisponível, coleta parcial ou atraso no DJEN.',
      action: 'Próxima ação: abrir o drilldown do dia e priorizar recoleta dos tribunais ausentes.',
    });
  }

  const recent = daysWithData.slice(-8);
  const latest = recent.at(-1);
  const previous = recent.slice(0, -1);
  if (latest && previous.length >= 3) {
    const previousAvg = previous.reduce((sum, day) => sum + day.pct, 0) / previous.length;
    const drop = previousAvg - latest.pct;
    if (drop >= 10) {
      cards.push({
        id: 'recent-drop',
        tone: drop >= 25 ? 'error' : 'warning',
        icon: '↘',
        title: 'Queda recente de cobertura',
        summary: `${latest.date} ficou ${drop.toFixed(1)} p.p. abaixo da média recente (${previousAvg.toFixed(1)}%).`,
        impact: 'Impacto: o dia mais recente pode parecer incompleto para usuários e relatórios.',
        cause: 'Possível causa: lote ainda em processamento ou falha temporária de upload.',
        action: 'Próxima ação: verificar o status do pipeline antes de fechar o dia como completo.',
      });
    }
  }

  const latestRun = [...days].sort((a, b) => b.date.localeCompare(a.date));
  let persistentFailures = 0;
  for (const day of latestRun) {
    if (day.status !== 'failed') break;
    persistentFailures += 1;
  }
  if (persistentFailures >= 3) {
    cards.push({
      id: 'persistent-absence',
      tone: 'error',
      icon: '⏱',
      title: 'Ausência persistente',
      summary: `${persistentFailures} dias consecutivos recentes têm tribunais ausentes.`,
      impact: 'Impacto: a lacuna pode afetar séries históricas e alertas recorrentes.',
      cause: 'Possível causa: integração de tribunal interrompida ou credencial/endpoint instável.',
      action: 'Próxima ação: comparar os tribunais repetidos no drilldown e abrir tarefa de correção.',
    });
  }

  if (noDataDays.length > 0) {
    cards.push({
      id: 'no-data',
      tone: 'info',
      icon: '○',
      title: 'Dias sem dados registrados',
      summary: `${noDataDays.length} dia${noDataDays.length === 1 ? '' : 's'} sem total de cobertura neste mês.`,
      impact: 'Impacto: não há evidência suficiente para dizer se houve coleta ou ausência oficial.',
      cause: 'Possível causa: dia fora da janela, catálogo ainda não publicado ou ingestão zerada.',
      action: 'Próxima ação: confirmar se o dia era esperado e reprocessar o manifesto se necessário.',
    });
  }

  if (cards.length === 0 && daysWithData.length > 0) {
    cards.push({
      id: 'healthy',
      tone: 'success',
      icon: '✓',
      title: 'Cobertura sem anomalias fortes',
      summary: `${daysWithData.length} dia${daysWithData.length === 1 ? '' : 's'} com cobertura completa ou dentro do esperado.`,
      impact: 'Impacto: consultas e métricas tendem a refletir a base disponível.',
      cause: 'Possível causa: pipeline e upload operando dentro do padrão recente.',
      action: 'Próxima ação: manter monitoramento e revisar apenas novas quedas.',
    });
  }

  return cards;
}

export function buildTribunalAttentionCards(params: {
  tribunal: string;
  missingDays: number;
  absentCount: number;
  expectedDays: number;
  coverageSize: number;
  completionPct: number;
  velocityRegressionPct?: number;
  isStopped?: boolean;
}): AttentionCard[] {
  const cards: AttentionCard[] = [];
  const completion = params.expectedDays > 0
    ? (params.coverageSize / params.expectedDays) * 100
    : params.completionPct;

  if (params.missingDays > 0) {
    cards.push({
      id: 'tribunal-gap',
      tone: params.missingDays > 30 ? 'error' : 'warning',
      icon: '⚠',
      title: 'Lacuna de cobertura do tribunal',
      summary: `${params.tribunal} tem ${params.missingDays} dia${params.missingDays === 1 ? '' : 's'} sem publicação coletada na janela monitorada.`,
      impact: 'Impacto: pesquisas por processo, OAB ou parte podem não encontrar intimações desses dias.',
      cause: 'Possível causa: backfill pendente, diário indisponível ou dia ainda não conciliado.',
      action: 'Próxima ação: revisar o calendário e priorizar os dias marcados como ausentes.',
    });
  }

  if (params.absentCount >= 3) {
    cards.push({
      id: 'tribunal-persistent-absence',
      tone: 'error',
      icon: '⏱',
      title: 'Ausência persistente declarada',
      summary: `${params.absentCount} dia${params.absentCount === 1 ? '' : 's'} aparecem como ausentes para ${params.tribunal}.`,
      impact: 'Impacto: a ausência repetida reduz a confiança na completude histórica.',
      cause: 'Possível causa: o tribunal não publicou nesses dias ou a fonte retornou vazio continuamente.',
      action: 'Próxima ação: validar se a ausência é oficial antes de abrir recoleta.',
    });
  }

  if ((params.velocityRegressionPct ?? 0) >= 25 || completion < 90) {
    cards.push({
      id: 'tribunal-anomaly',
      tone: 'warning',
      icon: '↘',
      title: 'Destaque de anomalia',
      summary: completion < 90
        ? `Completude estimada em ${completion.toFixed(1)}% para a janela atual.`
        : `Velocidade recente caiu ${params.velocityRegressionPct?.toFixed(0)}% contra o ritmo anterior.`,
      impact: 'Impacto: o tempo para concluir o histórico pode aumentar.',
      cause: 'Possível causa: desaceleração no backfill ou filas maiores de coleta.',
      action: 'Próxima ação: comparar velocidade, cursor e dias faltantes antes de ajustar ETA.',
    });
  }

  if (params.isStopped) {
    cards.push({
      id: 'tribunal-stopped',
      tone: 'error',
      icon: '■',
      title: 'Pipeline interrompido',
      summary: `${params.tribunal} foi marcado como interrompido após ausência prolongada.`,
      impact: 'Impacto: novas buscas podem permanecer sem atualização até intervenção.',
      cause: 'Possível causa: 60 dias sem publicações identificadas ou fonte instável.',
      action: 'Próxima ação: confirmar a regra de parada e reativar apenas se a fonte voltou.',
    });
  }

  return cards;
}
