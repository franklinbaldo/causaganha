<script lang="ts">
  interface HeatmapLegendProps {
    coveredDays: number;
    totalDays: number;
  }

  let { coveredDays, totalDays }: HeatmapLegendProps = $props();
</script>

<div class="legend-card">
  <div class="legend-body">
    <span class="legend-summary">
      <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados neste mês
    </span>
    <div class="legend-items">
      <span class="legend-label">Legenda:</span>
      <div class="legend-item"><div class="legend-swatch heatmap-missing"></div><span>Faltante</span></div>
      <div class="legend-item"><div class="legend-swatch heatmap-absent"></div><span>Ausente</span></div>
      <div class="legend-item"><div class="legend-swatch heatmap-collected"></div><span>Coletado</span></div>
    </div>
  </div>
</div>

<style>
  .legend-card   { background: var(--color-base-200); border-radius: var(--radius-box); }

  .legend-body {
    padding: 0.75rem 1rem;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    font-size: var(--font-size-sm);
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .legend-summary { opacity: 0.7; }

  .legend-items {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .legend-label { opacity: 0.5; }

  .legend-item  { display: flex; align-items: center; gap: 0.375rem; }

  .legend-swatch {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: var(--radius-sm);
  }
</style>
