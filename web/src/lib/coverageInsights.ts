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
    ? ((params.coverageSize + params.absentCount) / params.expectedDays) * 100
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
