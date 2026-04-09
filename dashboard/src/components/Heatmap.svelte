<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import CellTooltip from './CellTooltip.svelte';
  import VelocityTimeline from './VelocityTimeline.svelte';
  import { type CellStatus, CELL_STATUS_COLORS } from '../lib/colorUtils';
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

  function handleOutsideInteraction() { hoveredCell = null; }

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

  let start = $derived(new Date(globalStartDateStr + 'T00:00:00Z'));
  let end   = $derived(new Date(globalEndDateStr   + 'T00:00:00Z'));
  let invalidRange = $derived(start > end);

  // ── Year/month picker state ──────────────────────────────────────────────
  const _now = new Date();
  let selectedYear  = $state(_now.getUTCFullYear());
  let selectedMonth = $state(_now.getUTCMonth()); // 0-indexed

  let minYear = $derived(start.getUTCFullYear());
  let maxYear = $derived(end.getUTCFullYear());

  // Clamp year to valid range when props change
  $effect(() => {
    if (selectedYear < minYear) { selectedYear = minYear; }
    if (selectedYear > maxYear) { selectedYear = maxYear; }
  });

  // Reset focused cell when navigation changes
  $effect(() => {
    selectedYear; selectedMonth;
    focusedCell = null;
  });

  function prevYear() { if (selectedYear > minYear) selectedYear--; }
  function nextYear() { if (selectedYear < maxYear) selectedYear++; }
  function goToToday() {
    const now = new Date();
    selectedYear = now.getUTCFullYear();
    selectedMonth = now.getUTCMonth();
  }

  function selectMonth(mo: number) {
    const first = new Date(Date.UTC(selectedYear, mo, 1));
    const last  = new Date(Date.UTC(selectedYear, mo + 1, 0));
    if (first > end || last < start) return; // outside data range
    selectedMonth = mo;
  }

  // ── Month-picker coverage badges ────────────────────────────────────────
  const MONTH_NAMES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  let monthCoverage = $derived.by(() =>
    MONTH_NAMES.map((name, mo) => {
      const first = new Date(Date.UTC(selectedYear, mo, 1));
      const last  = new Date(Date.UTC(selectedYear, mo + 1, 0));
      if (first > end || last < start) return { name, mo, total: 0, collected: 0, pct: -1 };

      let total = 0, collected = 0;
      for (let d = 1; d <= last.getUTCDate(); d++) {
        const dt = new Date(Date.UTC(selectedYear, mo, d));
        if (dt < start || dt > end) continue;
        const ds = toDateString(dt);
        if (tribunalStartDateStr && ds < tribunalStartDateStr) continue;
        total++;
        if (coverageSet.has(ds)) collected++;
      }
      return { name, mo, total, collected, pct: total > 0 ? collected / total : 0 };
    })
  );

  function monthBadgeClass(pct: number): string {
    if (pct < 0)    return 'month-outside';
    if (pct >= 0.8) return 'month-high';
    if (pct >= 0.5) return 'month-mid';
    if (pct > 0)    return 'month-low';
    return 'month-zero';
  }

  // ── Single-month calendar ────────────────────────────────────────────────
  let selectedMonthCalendar = $derived.by(() => {
    const yr = selectedYear, mo = selectedMonth;
    const firstDay = new Date(Date.UTC(yr, mo, 1));
    const lastDay  = new Date(Date.UTC(yr, mo + 1, 0));
    const startDow = firstDay.getUTCDay();

    const weeks: (string | null)[][] = [];
    let week: (string | null)[] = Array(startDow).fill(null);

    for (let d = 1; d <= lastDay.getUTCDate(); d++) {
      const dt = new Date(Date.UTC(yr, mo, d));
      week.push((dt >= start && dt <= end) ? toDateString(dt) : null);
      if (week.length === 7) { weeks.push(week); week = []; }
    }
    if (week.length > 0) {
      while (week.length < 7) week.push(null);
      weeks.push(week);
    }

    const label = firstDay.toLocaleString('pt-BR', { month: 'long', year: 'numeric', timeZone: 'UTC' });
    return { label, weeks };
  });

  let allDays     = $derived(selectedMonthCalendar.weeks.flat().filter(Boolean) as string[]);
  let coveredDays = $derived(allDays.filter(d => coverageSet.has(d)).length);
  let totalDays   = $derived(allDays.length);

  // ── Cell helpers (unchanged logic) ──────────────────────────────────────
  function getCellStatus(dateStr: string): CellStatus {
    if (tribunalStartDateStr && dateStr < tribunalStartDateStr) return 'outside';
    if (coverageSet.has(dateStr)) return 'collected';
    if (velocityMetrics?.absentSet?.has(dateStr)) return 'absent';
    return 'missing';
  }

  function getCellColor(dateStr: string | null): string {
    if (!dateStr) return '';
    const status = getCellStatus(dateStr);
    const base = CELL_STATUS_COLORS[status];
    return focusedCell === dateStr ? `${base} heatmap-focused heatmap-cell` : `${base} heatmap-cell`;
  }

  function getAriaLabel(dateStr: string | null): string {
    if (!dateStr) return 'Empty cell';
    const status = getCellStatus(dateStr);
    if (status === 'outside')  return `${dateStr}: Before Tribunal Joined`;
    if (status === 'absent')   return `${dateStr}: Confirmed Absent (No journal published)`;
    return `${dateStr}: ${status === 'collected' ? 'Collected' : 'Missing'}`;
  }

  function handleCellInteraction(e: any, dateStr: string | null, type: string) {
    if (e?.stopPropagation) e.stopPropagation();
    if (!dateStr) return;
    if (type === 'leave') { hoveredCell = null; return; }
    if (type === 'touch') {
      if (e?.cancelable) e.preventDefault();
      const pos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      hoveredCell = hoveredCell?.data?.date === dateStr ? null
        : { data: { date: dateStr, status: getCellStatus(dateStr), uploadedAt: null, sizeMb: null }, position: pos };
      return;
    }
    const pos = { x: e.clientX, y: e.clientY };
    if (type === 'click') {
      if (getCellStatus(dateStr) === 'collected' && baseUrl) { window.location.hash = dateStr; return; }
      if (hoveredCell?.data?.date === dateStr) { hoveredCell = null; return; }
    }
    hoveredCell = { data: { date: dateStr, status: getCellStatus(dateStr), uploadedAt: null, sizeMb: null }, position: pos };
  }

  function handleGridKeyDown(e: any) {
    if (!allDays.length) return;
    let idx = focusedCell ? allDays.indexOf(focusedCell) : allDays.length - 1;
    if (idx === -1) idx = allDays.length - 1;
    let next = idx;
    switch (e.key) {
      case 'ArrowLeft':  next = Math.max(0, idx - 1);              e.preventDefault(); break;
      case 'ArrowRight': next = Math.min(allDays.length - 1, idx + 1); e.preventDefault(); break;
      case 'ArrowUp':    next = Math.max(0, idx - 7);              e.preventDefault(); break;
      case 'ArrowDown':  next = Math.min(allDays.length - 1, idx + 7); e.preventDefault(); break;
      case 'Enter': case ' ':
        if (focusedCell) {
          e.preventDefault();
          const rect = document.getElementById(`cell-${focusedCell}`)?.getBoundingClientRect()
            ?? { x: window.innerWidth / 2, y: window.innerHeight / 2 };
          handleCellInteraction({ clientX: rect.x + 6, clientY: rect.y + 6, stopPropagation: () => {} }, focusedCell, 'click');
        }
        break;
      case 'Escape': hoveredCell = null; e.preventDefault(); break;
      default: return;
    }
    if (next !== idx && allDays[next]) focusedCell = allDays[next];
  }

  const weekdayHeaders = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
</script>

{#if invalidRange}
  <div>Invalid date range.</div>
{:else}
  <div class="heatmap-wrapper">

    <!-- ── Year wheel ──────────────────────────────────────── -->
    <div class="year-nav">
      <button
        class="year-arrow"
        onclick={prevYear}
        disabled={selectedYear <= minYear}
        aria-label="Ano anterior"
      >&#8592;</button>
      <span class="year-label">{selectedYear}</span>
      <button
        class="year-arrow"
        onclick={nextYear}
        disabled={selectedYear >= maxYear}
        aria-label="Próximo ano"
      >&#8594;</button>
      <button class="today-btn" onclick={goToToday} aria-label="Ir para o mês atual">
        Hoje
      </button>
    </div>

    <!-- ── Month picker grid ───────────────────────────────── -->
    <div class="month-picker" role="listbox" aria-label="Selecionar mês">
      {#each monthCoverage as mc}
        {@const isSelected = mc.mo === selectedMonth}
        {@const isDisabled = mc.pct < 0}
        <button
          class="month-btn {monthBadgeClass(mc.pct)} {isSelected ? 'month-selected' : ''}"
          onclick={() => selectMonth(mc.mo)}
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

    <!-- ── Single-month calendar ───────────────────────────── -->
    {#key `${selectedYear}-${selectedMonth}`}
    <div class="month-card" transition:fade={{ duration: 120 }}>
      <h5 class="month-title">{selectedMonthCalendar.label}</h5>
      <table
        class="calendar-table"
        role="grid"
        aria-label="Calendário de cobertura — {selectedMonthCalendar.label} — {tribunalName}"
        tabindex="0"
        onkeydown={handleGridKeyDown}
        onfocus={() => { if (!focusedCell) focusedCell = allDays[allDays.length - 1]; }}
        onblur={() => { focusedCell = null; hoveredCell = null; }}
      >
        <thead>
          <tr>
            {#each weekdayHeaders as d}
              <th class="weekday-header">{d}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each selectedMonthCalendar.weeks as week, wi}
            <tr role="row">
              {#each week as day, di}
                <td
                  id={day ? `cell-${day}` : undefined}
                  role="gridcell"
                  class="day-cell {day ? `day-cell--active ${getCellColor(day)} ${day && getCellStatus(day) === 'collected' && baseUrl ? 'day-cell--clickable' : 'day-cell--default'}` : ''}"
                  aria-label={getAriaLabel(day)}
                  aria-selected={focusedCell === day}
                  onmouseenter={(e: any) => handleCellInteraction(e, day, 'enter')}
                  onmousemove={(e: any)  => handleCellInteraction(e, day, 'move')}
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
    {/key}

    <!-- ── Legend ──────────────────────────────────────────── -->
    <div class="legend-card">
      <div class="legend-body">
        <span class="legend-summary">
          <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados neste mês
        </span>
        <div class="legend-items">
          <span class="legend-label">Legenda:</span>
          <div class="legend-item"><div class="legend-swatch heatmap-missing"></div><span>Faltante</span></div>
          <div class="legend-item"><div class="legend-swatch heatmap-absent"></div><span>Ausente</span></div>
          <div class="legend-item"><div class="legend-swatch heatmap-collected"></div><span>Coletado</span></div>
        </div>
      </div>
    </div>

    {#if velocityMetrics?.hasEnoughHistory}
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
    gap: 1.25rem;
  }

  /* ── Year navigation ── */
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

  /* ── Month picker ── */
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

  /* ── Month coverage mini-bar ── */
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

  /* ── Single month calendar ── */
  .month-card {
    background: var(--color-base-100);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    padding: 1rem;
  }

  .month-title {
    font-size: var(--font-size-sm);
    font-weight: 600;
    text-transform: capitalize;
    margin-bottom: 0.75rem;
    text-align: center;
  }

  .calendar-table {
    width: 100%;
    max-width: 22rem;
    margin: 0 auto;
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
    padding: 0.2rem;
  }

  .day-cell--active   { border-radius: var(--radius-sm); }
  .day-cell--clickable { cursor: pointer; }
  .day-cell--default  { cursor: default; }

  /* ── Legend ── */
  .legend-card   { background: var(--color-base-200); border-radius: var(--radius-box); }

  .legend-body {
    padding: 0.75rem 1rem;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    font-size: var(--font-size-sm);
    flex-wrap: wrap;
    gap: 0.75rem;
  }

  .legend-summary { opacity: 0.7; }

  .legend-items {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .legend-label { opacity: 0.5; }

  .legend-item  { display: flex; align-items: center; gap: 0.375rem; }

  .legend-swatch {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: var(--radius-sm);
  }

  /* ── Velocity section ── */
  .velocity-section {
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.5rem;
    margin-top: 1rem;
  }
</style>
