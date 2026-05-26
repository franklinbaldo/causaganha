<script lang="ts">
  let { coveredDays, totalDays }: { coveredDays: number; totalDays: number } = $props();
</script>

<div class="legend-strip">
  <span class="legend-summary">
    <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados neste mês
  </span>
  <ul class="legend-swatches" aria-label="Legenda">
    <li class="heatmap-missing">Faltante</li>
    <li class="heatmap-absent">Ausente</li>
    <li class="heatmap-collected">Coletado</li>
  </ul>
</div>

<style>
  .legend-strip {
    background: var(--color-base-200);
    border-radius: var(--radius-box);
    padding: 0.75rem 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: var(--font-size-sm);
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .legend-summary { opacity: 0.7; }

  .legend-swatches {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .legend-swatches li {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: var(--font-size-xs);
  }

  .legend-swatches li::before {
    content: '';
    display: inline-block;
    width: 0.75rem;
    height: 0.75rem;
    border-radius: var(--radius-sm);
    background: currentColor;
  }
</style>
