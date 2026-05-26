<script lang="ts">
  interface HeatmapYearNavProps {
    selectedYear: number;
    minYear: number;
    maxYear: number;
    onprev: () => void;
    onnext: () => void;
    ontoday: () => void;
  }

  let { selectedYear, minYear, maxYear, onprev, onnext, ontoday }: HeatmapYearNavProps = $props();
</script>

<div class="year-nav">
  <button
    class="year-arrow"
    onclick={onprev}
    disabled={selectedYear <= minYear}
    aria-label="Ano anterior"
  >&#8592;</button>
  <span class="year-label">{selectedYear}</span>
  <button
    class="year-arrow"
    onclick={onnext}
    disabled={selectedYear >= maxYear}
    aria-label="Próximo ano"
  >&#8594;</button>
  <button class="today-btn" onclick={ontoday} aria-label="Ir para o mês atual">
    Hoje
  </button>
</div>
