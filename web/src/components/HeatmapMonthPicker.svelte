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

<div class="month-picker" role="listbox" aria-label="Selecionar mês">
  {#each monthCoverage as mc}
    {@const isSelected = mc.mo === selectedMonth}
    {@const isDisabled = mc.pct < 0}
    <button
      class="month-btn {monthBadgeClass(mc.pct)} {isSelected ? 'month-selected' : ''}"
      onclick={() => onselect(mc.mo)}
      disabled={isDisabled}
      role="option"
      aria-selected={isSelected}
      aria-label="{mc.name}: {mc.pct >= 0 ? Math.round(mc.pct * 100) + '% coletado' : 'fora do intervalo'}"
      title="{mc.collected}/{mc.total} dias coletados"
    >
      <span class="month-name">{mc.name}</span>
      {#if mc.pct >= 0 && mc.total > 0}
        <div class="month-progress">
          <div class="month-progress-fill" style="width:{Math.round(mc.pct * 100)}%"></div>
        </div>
      {/if}
    </button>
  {/each}
</div>
