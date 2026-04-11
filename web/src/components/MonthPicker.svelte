<script lang="ts">
  /**
   * Reusable year-wheel + month-grid picker.
   *
   * Props:
   *   selectedYear    – bindable, current year
   *   selectedMonth   – bindable, current month (0-indexed)
   *   monthSummaries  – Record<"YYYY-MM", number>
   *                     value: 0-1 = metric (coverage/quality), -1 = no data for that month
   */

  interface MonthPickerProps {
    selectedYear: number;
    selectedMonth: number;
    monthSummaries: Record<string, number>;
  }

  let {
    selectedYear = $bindable(new Date().getUTCFullYear()),
    selectedMonth = $bindable(new Date().getUTCMonth()),
    monthSummaries,
  }: MonthPickerProps = $props();

  const MONTH_NAMES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  let minYear = $derived.by(() => {
    const keys = Object.keys(monthSummaries);
    if (!keys.length) return new Date().getUTCFullYear();
    return Math.min(...keys.map(k => parseInt(k.substring(0, 4))));
  });

  let maxYear = $derived.by(() => {
    const keys = Object.keys(monthSummaries);
    if (!keys.length) return new Date().getUTCFullYear();
    return Math.max(...keys.map(k => parseInt(k.substring(0, 4))));
  });

  // Clamp year to valid range
  $effect(() => {
    if (selectedYear < minYear) selectedYear = minYear;
    if (selectedYear > maxYear) selectedYear = maxYear;
  });

  let monthRow = $derived(
    MONTH_NAMES.map((name, mo) => {
      const key = `${selectedYear}-${String(mo + 1).padStart(2, '0')}`;
      const pct = monthSummaries[key] ?? -1;
      return { name, mo, pct };
    })
  );

  function prevYear() { if (selectedYear > minYear) selectedYear--; }
  function nextYear() { if (selectedYear < maxYear) selectedYear++; }
  function goToToday() {
    const now = new Date();
    selectedYear = now.getUTCFullYear();
    selectedMonth = now.getUTCMonth();
  }
  function selectMonth(mo: number, pct: number) {
    if (pct < 0) return;
    selectedMonth = mo;
  }

  function badgeClass(pct: number): string {
    if (pct < 0)    return 'mp-outside';
    if (pct >= 0.8) return 'mp-high';
    if (pct >= 0.5) return 'mp-mid';
    if (pct > 0)    return 'mp-low';
    return 'mp-zero';
  }
</script>

<div class="mp-wrapper">
  <!-- Year wheel -->
  <div class="mp-year-nav">
    <button class="mp-arrow" onclick={prevYear} disabled={selectedYear <= minYear} aria-label="Ano anterior">&#8592;</button>
    <span class="mp-year">{selectedYear}</span>
    <button class="mp-arrow" onclick={nextYear} disabled={selectedYear >= maxYear} aria-label="Próximo ano">&#8594;</button>
    <button class="mp-today" onclick={goToToday} aria-label="Ir para o mês atual">Hoje</button>
  </div>

  <!-- Month grid -->
  <div class="mp-grid" role="listbox" aria-label="Selecionar mês">
    {#each monthRow as { name, mo, pct }}
      {@const isSelected = mo === selectedMonth}
      <button
        class="mp-month {badgeClass(pct)} {isSelected ? 'mp-selected' : ''}"
        onclick={() => selectMonth(mo, pct)}
        disabled={pct < 0}
        role="option"
        aria-selected={isSelected}
        title="{pct >= 0 ? Math.round(pct * 100) + '%' : 'sem dados'}"
      >
        <span class="mp-name">{name}</span>
        {#if pct >= 0}
          <div class="mp-bar"><div class="mp-bar-fill" style="width:{Math.round(pct * 100)}%"></div></div>
        {/if}
      </button>
    {/each}
  </div>
</div>

<style>
  .mp-wrapper { display: flex; flex-direction: column; gap: 0.5rem; }

  /* Year nav */
  .mp-year-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
  }

  .mp-arrow {
    width: 2rem; height: 2rem;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--radius-full);
    border: 1px solid var(--color-base-300);
    background: transparent;
    cursor: pointer;
    transition: background 0.15s;
  }
  .mp-arrow:hover:not(:disabled) { background: var(--color-base-200); }
  .mp-arrow:disabled { opacity: 0.3; cursor: default; }

  .mp-year {
    font-size: var(--font-size-xl, 1.25rem);
    font-weight: 700;
    min-width: 4rem;
    text-align: center;
  }

  .mp-today {
    font-size: var(--font-size-xs);
    padding: 0.25rem 0.625rem;
    border-radius: var(--radius-full);
    border: 1px solid var(--color-base-300);
    background: transparent;
    cursor: pointer;
    opacity: 0.7;
    transition: opacity 0.15s, background 0.15s;
  }
  .mp-today:hover { opacity: 1; background: var(--color-base-200); }

  /* Month grid */
  .mp-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(4rem, 1fr));
    gap: 0.375rem;
  }

  .mp-month {
    display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
    padding: 0.5rem 0.25rem 0.375rem;
    border-radius: var(--radius-box);
    border: 2px solid transparent;
    background: var(--color-base-200);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    overflow: hidden;
  }
  .mp-month:disabled { opacity: 0.35; cursor: default; }
  .mp-month:not(:disabled):hover { border-color: var(--color-primary); }
  .mp-selected {
    border-color: var(--color-primary) !important;
    background: color-mix(in srgb, var(--color-primary) 10%, var(--color-base-100));
  }

  .mp-name { font-size: var(--font-size-xs); font-weight: 600; line-height: 1; }

  .mp-bar {
    width: 100%; height: 3px;
    background: var(--color-base-300);
    border-radius: 2px; overflow: hidden;
  }
  .mp-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }

  .mp-high  .mp-bar-fill { background: var(--color-success); }
  .mp-mid   .mp-bar-fill { background: var(--color-warning); }
  .mp-low   .mp-bar-fill { background: var(--color-error); }
  .mp-zero  .mp-bar-fill { background: var(--color-base-300); }
  .mp-outside { opacity: 0.3; }
</style>
