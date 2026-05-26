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

<style>
  .year-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }

  .year-arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--color-base-300);
    background: transparent;
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    transition: background 0.15s;
  }

  .year-arrow:hover:not(:disabled) {
    background: var(--color-base-200);
  }

  .year-arrow:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .year-label {
    font-size: var(--font-size-xl, 1.25rem);
    font-weight: 700;
    min-width: 4rem;
    text-align: center;
  }

  .today-btn {
    font-size: var(--font-size-xs);
    padding: 0.25rem 0.625rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--color-base-300);
    background: transparent;
    cursor: pointer;
    opacity: 0.7;
    transition: opacity 0.15s, background 0.15s;
  }

  .today-btn:hover {
    opacity: 1;
    background: var(--color-base-200);
  }
</style>
