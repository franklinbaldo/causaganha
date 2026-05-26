<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import CellTooltip from './CellTooltip.svelte';
  import VelocityTimeline from './VelocityTimeline.svelte';
  import HeatmapLegend from './HeatmapLegend.svelte';
  import HeatmapYearNav from './HeatmapYearNav.svelte';
  import HeatmapMonthPicker from './HeatmapMonthPicker.svelte';
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
  const currentYear  = _now.getUTCFullYear();
  const currentMonth = _now.getUTCMonth(); // 0-indexed
  let selectedYear  = $state(currentYear);
  let selectedMonth = $state(currentMonth);

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
    <HeatmapYearNav
      selectedYear={selectedYear}
      minYear={minYear}
      maxYear={maxYear}
      onprev={() => selectedYear--}
      onnext={() => selectedYear++}
      ontoday={() => { selectedYear = currentYear; selectedMonth = currentMonth; }}
    />

    <!-- ── Month picker grid ───────────────────────────────── -->
    <HeatmapMonthPicker
      monthCoverage={monthCoverage}
      selectedMonth={selectedMonth}
      onselect={(mo) => selectMonth(mo)}
    />

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
            <tr>
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
    <HeatmapLegend coveredDays={coveredDays} totalDays={totalDays} />

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
