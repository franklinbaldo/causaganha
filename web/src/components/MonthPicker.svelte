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

<div>
  <!-- Year wheel -->
  <div>
    <button class="outline" onclick={prevYear} disabled={selectedYear <= minYear} aria-label="Ano anterior">&#8592;</button>
    <strong>{selectedYear}</strong>
    <button class="outline" onclick={nextYear} disabled={selectedYear >= maxYear} aria-label="Próximo ano">&#8594;</button>
    <button class="secondary outline" onclick={goToToday} aria-label="Ir para o mês atual">Hoje</button>
  </div>

  <!-- Month grid -->
  <div class="auto-grid-sm" role="listbox" aria-label="Selecionar mês">
    {#each monthRow as { name, mo, pct }}
      {@const isSelected = mo === selectedMonth}
      <button
        class="{isSelected ? '' : 'outline'} {badgeClass(pct)}"
        onclick={() => selectMonth(mo, pct)}
        disabled={pct < 0}
        role="option"
        aria-selected={isSelected}
        title="{pct >= 0 ? Math.round(pct * 100) + '%' : 'sem dados'}"
        data-tone={isSelected ? 'info' : undefined}
      >
        {name}
        {#if pct >= 0}
          <progress value={Math.round(pct * 100)} max="100"></progress>
        {/if}
      </button>
    {/each}
  </div>
</div>
