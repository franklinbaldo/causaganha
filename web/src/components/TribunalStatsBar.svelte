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
