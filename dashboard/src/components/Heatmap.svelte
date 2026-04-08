<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import CellTooltip from './CellTooltip.svelte';
  import VelocityTimeline from './VelocityTimeline.svelte';
  import { type CellStatus, CELL_STATUS_COLORS, getBarColor } from '../lib/colorUtils';
  import { toDateString } from '../lib/dateUtils';

  interface CellData {
    date: string;
    status: string;
    uploadedAt: string | null;
    sizeMb: number | null;
  }

  interface HoveredCellState {
    data: CellData;
    position: { x: number; y: number };
  }

  interface HeatmapProps {
    globalStartDateStr: string;
    globalEndDateStr: string;
    tribunalStartDateStr: string | null;
    coverageSet: Set<string>;
    tribunalName: string;
    baseUrl: string | null;
    velocityMetrics: any;
  }

  let {
    globalStartDateStr,
    globalEndDateStr,
    tribunalStartDateStr,
    coverageSet,
    tribunalName,
    baseUrl,
    velocityMetrics
  }: HeatmapProps = $props();

  let hoveredCell = $state<HoveredCellState | null>(null);
  let focusedCell = $state<string | null>(null);

  function handleOutsideInteraction() {
    hoveredCell = null;
  }

  onMount(() => {
    document.addEventListener('touchstart', handleOutsideInteraction, { passive: true });
    document.addEventListener('click', handleOutsideInteraction, { passive: true });
  });

  onDestroy(() => {
    if (typeof document !== 'undefined') {
      document.removeEventListener('touchstart', handleOutsideInteraction);
      document.removeEventListener('click', handleOutsideInteraction);
    }
  });

  let start = $derived(new Date(globalStartDateStr + "T00:00:00Z"));
  let end = $derived(new Date(globalEndDateStr + "T00:00:00Z"));
  let invalidRange = $derived(start > end);

  let months = $derived.by(() => {
    if (invalidRange) return [];

    const result: { year: number; month: number; label: string; weeks: (string | null)[][] }[] = [];
    const cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), 1));
    const endMonth = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), 1));

    while (cursor <= endMonth) {
      const yr = cursor.getUTCFullYear();
      const mo = cursor.getUTCMonth();
      const firstDay = new Date(Date.UTC(yr, mo, 1));
      const lastDay = new Date(Date.UTC(yr, mo + 1, 0));
      const startDow = firstDay.getUTCDay();

      const weeks: (string | null)[][] = [];
      let week: (string | null)[] = Array(startDow).fill(null);

      for (let d = 1; d <= lastDay.getUTCDate(); d++) {
        const dt = new Date(Date.UTC(yr, mo, d));
        const ds = toDateString(dt);
        if (dt >= start && dt <= end) {
          week.push(ds);
        } else {
          week.push(null);
        }
        if (week.length === 7) {
          weeks.push(week);
          week = [];
        }
      }
      if (week.length > 0) {
        while (week.length < 7) week.push(null);
        weeks.push(week);
      }

      const label = firstDay.toLocaleString('pt-BR', { month: 'long', year: 'numeric', timeZone: 'UTC' });
      result.push({ year: yr, month: mo, label, weeks });
      cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    }

    return result;
  });

  let allDays = $derived(months.flatMap(m => m.weeks.flat().filter(Boolean) as string[]));
  let coveredDays = $derived(allDays.filter(d => coverageSet.has(d)).length);
  let totalDays = $derived(allDays.length);

  function getCellStatus(dateStr: string): CellStatus {
    if (tribunalStartDateStr && dateStr < tribunalStartDateStr) {
      return 'outside';
    }
    if (coverageSet.has(dateStr)) return 'collected';
    if (velocityMetrics?.absentSet?.has(dateStr)) return 'absent';
    return 'missing';
  }

  function getCellColor(dateStr: string | null): string {
    if (!dateStr) return "";
    const status = getCellStatus(dateStr);
    const base = CELL_STATUS_COLORS[status];
    const isFocused = focusedCell === dateStr;
    return isFocused ? `${base} heatmap-focused heatmap-cell` : `${base} heatmap-cell`;
  }

  function getAriaLabel(dateStr: string | null): string {
    if (!dateStr) return "Empty cell";
    const status = getCellStatus(dateStr);
    if (status === 'outside') return `${dateStr}: Before Tribunal Joined`;
    if (status === 'absent') return `${dateStr}: Confirmed Absent (No journal published)`;
    return `${dateStr}: ${status === 'collected' ? 'Collected' : 'Missing'}`;
  }

  function handleCellInteraction(e: any, dateStr: string | null, type: string) {
    if (e && e.stopPropagation) e.stopPropagation();
    if (!dateStr) return;
    if (type === 'leave') {
      hoveredCell = null;
      return;
    }
    if (type === 'touch') {
      if (e && e.cancelable) e.preventDefault();
      const pos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      if (hoveredCell?.data?.date === dateStr) {
        hoveredCell = null;
      } else {
        hoveredCell = {
          data: { date: dateStr, status: getCellStatus(dateStr), uploadedAt: null, sizeMb: null },
          position: pos
        };
      }
      return;
    }
    const pos = { x: e.clientX, y: e.clientY };
    if (type === 'click') {
      const status = getCellStatus(dateStr);
      if (status === 'collected' && baseUrl) {
        window.location.hash = dateStr;
        return;
      }
      if (hoveredCell?.data?.date === dateStr) {
        hoveredCell = null;
        return;
      }
    }
    hoveredCell = {
      data: { date: dateStr, status: getCellStatus(dateStr), uploadedAt: null, sizeMb: null },
      position: pos
    };
  }

  function handleGridKeyDown(e: any) {
    if (!allDays.length) return;
    let currentIndex = focusedCell ? allDays.indexOf(focusedCell) : allDays.length - 1;
    if (currentIndex === -1) currentIndex = allDays.length - 1;
    let newIndex = currentIndex;
    switch (e.key) {
      case 'ArrowLeft': newIndex = Math.max(0, currentIndex - 1); e.preventDefault(); break;
      case 'ArrowRight': newIndex = Math.min(allDays.length - 1, currentIndex + 1); e.preventDefault(); break;
      case 'ArrowUp': newIndex = Math.max(0, currentIndex - 7); e.preventDefault(); break;
      case 'ArrowDown': newIndex = Math.min(allDays.length - 1, currentIndex + 7); e.preventDefault(); break;
      case 'Enter':
      case ' ':
        if (focusedCell) {
          e.preventDefault();
          const cellEl = document.getElementById(`cell-${focusedCell}`);
          const rect = cellEl ? cellEl.getBoundingClientRect() : { x: window.innerWidth / 2, y: window.innerHeight / 2 };
          handleCellInteraction({ clientX: rect.x + 6, clientY: rect.y + 6, stopPropagation: () => {} }, focusedCell, 'click');
        }
        break;
      case 'Escape': hoveredCell = null; e.preventDefault(); break;
      default: return;
    }
    if (newIndex !== currentIndex && allDays[newIndex]) {
      focusedCell = allDays[newIndex];
    }
  }

  const weekdayHeaders = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
</script>

{#if invalidRange}
  <div>Invalid date range.</div>
{:else}
  <div class="heatmap-wrapper">
    <div
      class="months-grid"
      role="grid"
      aria-label="Calendário de cobertura para {tribunalName}"
      tabindex="0"
      onkeydown={handleGridKeyDown}
      onfocus={() => { if (!focusedCell) focusedCell = allDays[allDays.length - 1]; }}
      onblur={() => { focusedCell = null; hoveredCell = null; }}
    >
      {#each months as m (`${m.year}-${m.month}`)}
        <div class="month-card">
          <h5 class="month-label">{m.label}</h5>
          <table class="calendar-table">
            <thead>
              <tr>
                {#each weekdayHeaders as d}
                  <th class="weekday-header">{d}</th>
                {/each}
              </tr>
            </thead>
            <tbody>
              {#each m.weeks as week, wi (`${m.year}-${m.month}-w${wi}`)}
                <tr role="row">
                  {#each week as day, di}
                    <td
                      id={day ? `cell-${day}` : undefined}
                      role="gridcell"
                      class="day-cell {day ? `day-cell--active ${getCellColor(day)} ${day && getCellStatus(day) === 'collected' && baseUrl ? 'day-cell--clickable' : 'day-cell--default'}` : ''}"
                      aria-label={getAriaLabel(day)}
                      aria-selected={focusedCell === day}
                      onmouseenter={(e: any) => handleCellInteraction(e, day, 'enter')}
                      onmousemove={(e: any) => handleCellInteraction(e, day, 'move')}
                      onmouseleave={(e: any) => handleCellInteraction(e, day, 'leave')}
                      ontouchstart={(e: any) => handleCellInteraction(e, day, 'touch')}
                      onclick={(e: any) => { handleCellInteraction(e, day, 'click'); focusedCell = day; }}
                    >
                      {day ? new Date(day + 'T00:00:00Z').getUTCDate() : ''}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/each}
    </div>

    <div class="legend-card">
      <div class="legend-body">
        <span class="legend-summary">
          <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados
        </span>
        <div class="legend-items">
          <span class="legend-label">Legenda:</span>
          <div class="legend-item">
            <div class="legend-swatch heatmap-missing"></div>
            <span>Faltante</span>
          </div>
          <div class="legend-item">
            <div class="legend-swatch heatmap-absent"></div>
            <span>Ausente</span>
          </div>
          <div class="legend-item">
            <div class="legend-swatch heatmap-collected"></div>
            <span>Coletado</span>
          </div>
        </div>
      </div>
    </div>

    {#if velocityMetrics && velocityMetrics.hasEnoughHistory}
      <div class="velocity-section">
        <VelocityTimeline metrics={velocityMetrics} />
      </div>
    {/if}

    {#if hoveredCell}
      <CellTooltip cellData={hoveredCell.data} position={hoveredCell.position} />
    {/if}
  </div>
{/if}

<style>
  .heatmap-wrapper {
    display: flex;
    flex-direction: column;
    gap: 2rem;
  }

  .months-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  @media (min-width: 640px) {
    .months-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (min-width: 1024px) {
    .months-grid {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  @media (min-width: 1280px) {
    .months-grid {
      grid-template-columns: repeat(4, 1fr);
    }
  }

  .month-card {
    background: var(--color-base-100);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    padding: 0.75rem;
  }

  .month-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    text-transform: capitalize;
    margin-bottom: 0.5rem;
  }

  .calendar-table {
    width: 100%;
  }

  .weekday-header {
    font-size: var(--font-size-xs);
    opacity: 0.5;
    font-weight: 400;
    text-align: center;
    padding-bottom: 0.25rem;
  }

  .day-cell {
    text-align: center;
    font-size: var(--font-size-xs);
    padding: 0.125rem;
  }

  .day-cell--active {
    border-radius: var(--radius-sm);
  }

  .day-cell--clickable {
    cursor: pointer;
  }

  .day-cell--default {
    cursor: default;
  }

  .legend-card {
    background: var(--color-base-200);
    border-radius: var(--radius-box);
  }

  .legend-body {
    padding: 1rem;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    font-size: var(--font-size-sm);
    flex-wrap: wrap;
    gap: 1rem;
  }

  .legend-summary {
    opacity: 0.7;
  }

  .legend-items {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1.5rem;
  }

  .legend-label {
    opacity: 0.5;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .legend-swatch {
    width: 0.875rem;
    height: 0.875rem;
    border-radius: var(--radius-sm);
  }

  .velocity-section {
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.5rem;
    margin-top: 2.5rem;
  }
</style>
