<script lang="ts">
  let { coveredDays, totalDays }: { coveredDays: number; totalDays: number } = $props();
</script>

<footer>
  <small>
    <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados neste mês
  </small>
  <ul aria-label="Legenda">
    <li class="heatmap-missing">Faltante</li>
    <li class="heatmap-absent">Ausente</li>
    <li class="heatmap-collected">Coletado</li>
  </ul>
</footer>
