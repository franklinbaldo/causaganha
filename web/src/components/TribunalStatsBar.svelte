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

<dl class="auto-grid-sm">
  <div>
    <dt>Progresso da Coleta</dt>
    <dd class={`stat-value ${statusColor}`}>{completionPct}%</dd>
    <progress value={Math.round(syncedPct)} max="100"></progress>
    <small>
      <span>{coverageSize} itens sincronizados</span>
      ·
      <span>{absentCount} dias ausentes</span>
    </small>
  </div>

  <div>
    <dt>Status</dt>
    <dd class={`stat-value ${statusColor}`}>{completionStatusText}</dd>
    <small>{etaText}</small>
  </div>

  <div>
    <dt>Dias Faltantes</dt>
    <dd class="stat-value">{actualMissingDays}</dd>
    <small>A partir de {genesisDate || "Desconhecida"}</small>
  </div>
</dl>
