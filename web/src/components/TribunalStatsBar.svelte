<script lang="ts">
  let {
    completionPct,
    syncedPct,
    coverageSize,
    absentCount,
    statusColor,
    completionStatusText,
    etaText,
    actualMissingDays,
    genesisDate,
  }: {
    completionPct: number;
    syncedPct: number;
    coverageSize: number;
    absentCount: number;
    statusColor: string;
    completionStatusText: string;
    etaText: string;
    actualMissingDays: number;
    genesisDate: string | null;
  } = $props();
</script>

<dl class="stats-bar">
  <div class="stat">
    <dt>Progresso da Coleta</dt>
    <dd class="stat-value value-primary">{completionPct}%</dd>
    <progress class="progress-bar progress-primary" value={Math.round(syncedPct)} max="100"></progress>
    <small class="progress-legend">
      <span>{coverageSize} itens sincronizados</span>
      <span>{absentCount} dias ausentes</span>
    </small>
  </div>

  <div class="stat">
    <dt>Status</dt>
    <dd class={`stat-value ${statusColor}`}>{completionStatusText}</dd>
    <small>{etaText}</small>
  </div>

  <div class="stat">
    <dt>Dias Faltantes</dt>
    <dd class="stat-value">{actualMissingDays}</dd>
    <small>A partir de {genesisDate || "Desconhecida"}</small>
  </div>
</dl>

<style>
  .stats-bar {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    margin-bottom: 2rem;
  }

  @media (min-width: 768px) {
    .stats-bar { flex-direction: row; }
  }

  .stat {
    padding: 1rem 1.5rem;
    flex: 1;
  }

  .stat dt {
    opacity: 0.6;
    font-size: var(--font-size-sm);
    font-weight: 400;
  }

  .stat dd { margin: 0; }

  .stat-value {
    font-size: var(--font-size-2xl);
    font-weight: 700;
    line-height: 1.2;
  }

  .value-primary { color: var(--color-primary); }
  .value-success { color: var(--color-success); }
  .value-warning { color: var(--color-warning); }

  .progress-bar {
    width: 100%;
    height: 0.5rem;
    appearance: none;
    border-radius: var(--radius-full);
    margin-top: 0.5rem;
  }

  .progress-bar::-webkit-progress-bar {
    background: var(--color-base-300);
    border-radius: var(--radius-full);
  }

  .progress-primary::-webkit-progress-value {
    background: var(--color-primary);
    border-radius: var(--radius-full);
  }

  .progress-legend {
    display: flex;
    justify-content: space-between;
    margin-top: 0.25rem;
    font-size: var(--font-size-xs);
    opacity: 0.6;
  }
</style>
