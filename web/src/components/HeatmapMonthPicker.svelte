<script lang="ts">
  interface MonthEntry {
    name: string;
    mo: number;
    total: number;
    collected: number;
    pct: number;
  }

  interface HeatmapMonthPickerProps {
    monthCoverage: MonthEntry[];
    selectedMonth: number;
    onselect: (month: number) => void;
  }

  let { monthCoverage, selectedMonth, onselect }: HeatmapMonthPickerProps = $props();

  function monthBadgeClass(pct: number): string {
    if (pct < 0)    return 'month-outside';
    if (pct >= 0.8) return 'month-high';
    if (pct >= 0.5) return 'month-mid';
    if (pct > 0)    return 'month-low';
    return 'month-zero';
  }
</script>

<div class="auto-grid-sm" role="listbox" aria-label="Selecionar mês">
  {#each monthCoverage as mc}
    {@const isSelected = mc.mo === selectedMonth}
    {@const isDisabled = mc.pct < 0}
    <button
      class="{isSelected ? '' : 'outline'} {monthBadgeClass(mc.pct)}"
      onclick={() => onselect(mc.mo)}
      disabled={isDisabled}
      role="option"
      aria-selected={isSelected}
      aria-label="{mc.name}: {mc.pct >= 0 ? Math.round(mc.pct * 100) + '% coletado' : 'fora do intervalo'}"
      title="{mc.collected}/{mc.total} dias coletados"
    >
      {mc.name}
      {#if mc.pct >= 0 && mc.total > 0}
        <progress value={Math.round(mc.pct * 100)} max="100"></progress>
      {/if}
    </button>
  {/each}
</div>
