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
