import { useState, useEffect } from 'preact/compat';
import { CellTooltip } from './CellTooltip';
import { CellStatus, CELL_STATUS_COLORS, getBarColor } from '../lib/colorUtils';
import { toDateString } from '../lib/dateUtils';

interface VelocityWeek {
  collected: number;
  weekOffset: number;
}

interface VelocityTimelineProps {
  metrics: any;
}

export function VelocityTimeline({ metrics }: VelocityTimelineProps) {
  if (!metrics || !metrics.hasEnoughHistory) return null;

  const { weeklyData, historicalAvgVelocity, currentVelocity, trend } = metrics;
  const maxCollected = Math.max(7, ...weeklyData.map((w: VelocityWeek) => w.collected));

  let trendColor = "opacity-50";
  let trendText = "Estável";
  if (currentVelocity > historicalAvgVelocity * 1.2) {
    trendColor = "text-success";
    trendText = "Acelerando";
  } else if (currentVelocity < historicalAvgVelocity * 0.7) {
    trendColor = "text-error";
    trendText = "Em declínio";
  }

  return (
    <div aria-label="Velocidade de Coleta nas Últimas 12 Semanas">
      <div className="flex justify-between items-baseline flex-wrap gap-4 mb-6 items-baseline">
        <div>
          <h4 className="mb-0">Velocidade de Coleta</h4>
          <p className="opacity-50 mb-0 text-sm">Taxa de coleta das últimas 12 semanas</p>
        </div>
        <div className="text-right">
          <div className="font-bold">{currentVelocity.toFixed(1)} dias/sem (média)</div>
          <div className={`${trendColor} text-sm`}>
            {trend > 0 ? '+' : ''}{trend.toFixed(0)}% vs média ({trendText})
          </div>
        </div>
      </div>

      <div role="list" className="flex items-end mt-10 gap-1 h-[100px]">
        {weeklyData.map((week: VelocityWeek, idx: number) => {
          const heightPct = Math.max(5, (week.collected / maxCollected) * 100);

          return (
            <div
              key={`w-${idx}`}
              role="listitem"
              className="flex items-end flex-1 relative h-full"
              title={`${week.collected} dias coletados (Semana ${12 - week.weekOffset})`}
              aria-label={`${week.collected} dias coletados na semana ${12 - week.weekOffset}`}>
              <div
                className={`${getBarColor(week.collected)} w-full rounded-t opacity-80 transition-opacity`}
                style={{ height: `${heightPct}%` }}></div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-between items-baseline opacity-50 mt-2 text-xs">
        <span>12 semanas atrás</span>
        <span>Atual</span>
      </div>
    </div>
  );
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

export function Heatmap({ globalStartDateStr, globalEndDateStr, tribunalStartDateStr, coverageSet, tribunalName, baseUrl, velocityMetrics }: HeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<HoveredCellState | null>(null);
  const [focusedCell, setFocusedCell] = useState<string | null>(null);

  useEffect(() => {
    const handleOutsideInteraction = () => setHoveredCell(null);
    if (typeof document !== 'undefined') {
      document.addEventListener('touchstart', handleOutsideInteraction, { passive: true });
      document.addEventListener('click', handleOutsideInteraction, { passive: true });
    }
    return () => {
      if (typeof document !== 'undefined') {
        document.removeEventListener('touchstart', handleOutsideInteraction);
        document.removeEventListener('click', handleOutsideInteraction);
      }
    };
  }, []);

  const start = new Date(globalStartDateStr + "T00:00:00Z");
  const end = new Date(globalEndDateStr + "T00:00:00Z");

  if (start> end) {
    return <div>Invalid date range.</div>;
  }

  // Build months for calendar view
  const months: { year: number; month: number; label: string; weeks: (string | null)[][] }[] = [];
  const cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), 1));
  const endMonth = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), 1));

  while (cursor <= endMonth) {
    const yr = cursor.getUTCFullYear();
    const mo = cursor.getUTCMonth();
    const firstDay = new Date(Date.UTC(yr, mo, 1));
    const lastDay = new Date(Date.UTC(yr, mo + 1, 0));
    const startDow = firstDay.getUTCDay(); // 0=Sun

    const weeks: (string | null)[][] = [];
    let week: (string | null)[] = Array(startDow).fill(null);

    for (let d = 1; d <= lastDay.getUTCDate(); d++) {
      const dt = new Date(Date.UTC(yr, mo, d));
      const ds = toDateString(dt);
      // Only include days within the global range
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
    months.push({ year: yr, month: mo, label, weeks });
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }

  const allDays = months.flatMap(m => m.weeks.flat().filter(Boolean) as string[]);
  const coveredDays = allDays.filter(d => coverageSet.has(d)).length;
  const totalDays = allDays.length;

  const getCellStatus = (dateStr: string): CellStatus => {
    if (tribunalStartDateStr && dateStr < tribunalStartDateStr) {
      return 'outside';
    }
    if (coverageSet.has(dateStr)) return 'collected';
    if (velocityMetrics?.absentSet?.has(dateStr)) return 'absent';
    return 'missing';
  };

  const getCellColor = (dateStr: string | null): string => {
    if (!dateStr) return "";
    const status = getCellStatus(dateStr);
    const base = CELL_STATUS_COLORS[status];
    const isFocused = focusedCell === dateStr;
    return isFocused ? `${base} heatmap-focused heatmap-cell` : `${base} heatmap-cell`;
  };

  const getAriaLabel = (dateStr: string | null): string => {
    if (!dateStr) return "Empty cell";
    const status = getCellStatus(dateStr);
    if (status === 'outside') return `${dateStr}: Before Tribunal Joined`;
    if (status === 'absent') return `${dateStr}: Confirmed Absent (No journal published)`;
    return `${dateStr}: ${status === 'collected' ? 'Collected' : 'Missing'}`;
  };

  const handleCellInteraction = (e: any, dateStr: string | null, type: string) => {
    if (e && e.stopPropagation) e.stopPropagation();
    if (!dateStr) return;
    if (type === 'leave') {
      setHoveredCell(null);
      return;
    }
    if (type === 'touch') {
      if (e && e.cancelable) e.preventDefault();
      const pos = { x: e.touches[0].clientX, y: e.touches[0].clientY };
      if (hoveredCell?.data?.date === dateStr) {
        setHoveredCell(null);
      } else {
        setHoveredCell({
          data: { date: dateStr, status: getCellStatus(dateStr), uploadedAt: null, sizeMb: null },
          position: pos
        });
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
        setHoveredCell(null);
        return;
      }
    }
    setHoveredCell({
      data: { date: dateStr, status: getCellStatus(dateStr), uploadedAt: null, sizeMb: null },
      position: pos
    });
  };

  const handleGridKeyDown = (e: any) => {
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
      case 'Escape': setHoveredCell(null); e.preventDefault(); break;
      default: return;
    }
    if (newIndex !== currentIndex && allDays[newIndex]) {
      setFocusedCell(allDays[newIndex]);
    }
  };

  const weekdayHeaders = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  return (
    <div className="flex flex-col gap-8">
      <div
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
        role="grid"
        aria-label={`Calendário de cobertura para ${tribunalName}`}
        tabIndex={0}
        onKeyDown={handleGridKeyDown}
        onFocus={() => { if (!focusedCell) setFocusedCell(allDays[allDays.length - 1]); }}
        onBlur={() => { setFocusedCell(null); setHoveredCell(null); }}
      >
        {months.map((m) => (
          <div key={`${m.year}-${m.month}`} className="card bg-base-100 border border-base-300 p-3">
            <h5 className="text-sm font-semibold capitalize mb-2">{m.label}</h5>
            <table className="w-full">
              <thead>
                <tr>
                  {weekdayHeaders.map((d) => (
                    <th key={d} className="text-xs opacity-50 font-normal text-center pb-1">{d}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {m.weeks.map((week, wi) => (
                  <tr key={`${m.year}-${m.month}-w${wi}`} role="row">
                    {week.map((day, di) => (
                      <td
                        key={day || `empty-${m.year}-${m.month}-${wi}-${di}`}
                        id={day ? `cell-${day}` : undefined}
                        role="gridcell"
                        className={`text-center text-xs p-0.5 ${day ? `rounded-sm ${getCellColor(day)} ${day && getCellStatus(day) === 'collected' && baseUrl ? 'cursor-pointer' : 'cursor-default'}` : ''}`}
                        aria-label={getAriaLabel(day)}
                        aria-selected={focusedCell === day}
                        onMouseEnter={(e: any) => handleCellInteraction(e, day, 'enter')}
                        onMouseMove={(e: any) => handleCellInteraction(e, day, 'move')}
                        onMouseLeave={(e: any) => handleCellInteraction(e, day, 'leave')}
                        onTouchStart={(e: any) => handleCellInteraction(e, day, 'touch')}
                        onClick={(e: any) => { handleCellInteraction(e, day, 'click'); setFocusedCell(day); }}
                      >
                        {day ? new Date(day + 'T00:00:00Z').getUTCDate() : ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      <div className="card bg-base-200">
        <div className="card-body p-4 flex-row justify-between items-center text-sm flex-wrap gap-4">
          <span className="opacity-70">
            <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados
          </span>
          <div className="flex items-center flex-wrap gap-6">
            <span className="opacity-50">Legenda:</span>
            <div className="flex items-center gap-2">
              <div className="heatmap-missing w-3.5 h-3.5 rounded-sm"></div>
              <span>Faltante</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="heatmap-absent w-3.5 h-3.5 rounded-sm"></div>
              <span>Ausente</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="heatmap-collected w-3.5 h-3.5 rounded-sm"></div>
              <span>Coletado</span>
            </div>
          </div>
        </div>
      </div>

      {velocityMetrics && velocityMetrics.hasEnoughHistory && (
        <div className="border-t border-base-300 pt-6 mt-10">
          <VelocityTimeline metrics={velocityMetrics} />
        </div>
      )}

      {hoveredCell && <CellTooltip cellData={hoveredCell.data} position={hoveredCell.position} />}
    </div>
  );
}
