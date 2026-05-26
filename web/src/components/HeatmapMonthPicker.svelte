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

<style>
  .month-picker {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(4rem, 1fr));
    gap: 0.375rem;
  }

  .month-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem 0.25rem 0.375rem;
    border-radius: var(--radius-box);
    border: 2px solid transparent;
    background: var(--color-base-200);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    position: relative;
    overflow: hidden;
  }

  .month-btn:disabled {
    opacity: 0.35;
    cursor: default;
  }

  .month-btn:not(:disabled):hover {
    border-color: var(--color-primary);
  }

  .month-selected {
    border-color: var(--color-primary) !important;
    background: color-mix(in srgb, var(--color-primary) 10%, var(--color-base-100));
  }

  .month-name {
    font-size: var(--font-size-xs);
    font-weight: 600;
    line-height: 1;
  }

  .month-progress {
    width: 100%;
    height: 3px;
    background: var(--color-base-300);
    border-radius: 2px;
    overflow: hidden;
  }

  .month-progress-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s;
  }

  .month-high   .month-progress-fill { background: var(--color-success); }
  .month-mid    .month-progress-fill { background: var(--color-warning); }
  .month-low    .month-progress-fill { background: var(--color-error);   }
  .month-zero   .month-progress-fill { background: var(--color-base-300); }
  .month-outside { opacity: 0.3; }
</style>
