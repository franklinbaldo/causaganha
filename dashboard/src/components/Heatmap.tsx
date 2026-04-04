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

  let trendColor = "text-muted";
  let trendText = "Estável";
  if (currentVelocity > historicalAvgVelocity * 1.2) {
    trendColor = "text-success";
    trendText = "Acelerando";
  } else if (currentVelocity < historicalAvgVelocity * 0.7) {
    trendColor = "text-danger";
    trendText = "Em declínio";
  }

  return (
    <div aria-label="Velocity Timeline">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '1.25rem' }}>Velocity Timeline</h4>
          <p className="text-muted" style={{ margin: 0, fontSize: '0.875rem' }}>Taxa de coleta das últimas 12 semanas</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 'bold' }}>{currentVelocity.toFixed(1)} docs/sem (média)</div>
          <div className={trendColor} style={{ fontSize: '0.875rem' }}>
            {trend > 0 ? '+' : ''}{trend.toFixed(0)}% vs média ({trendText})
          </div>
        </div>
      </div>

      <div role="list" style={{ display: 'flex', gap: '4px', height: '100px', alignItems: 'flex-end', marginTop: '2rem' }}>
        {weeklyData.map((week: VelocityWeek, idx: number) => {
          const heightPct = Math.max(5, (week.collected / maxCollected) * 100);

          return (
            <div
              key={`w-${idx}`}
              role="listitem"
              style={{ flex: 1, position: 'relative', height: '100%', display: 'flex', alignItems: 'flex-end', group: 'hover' }}
              title={`${week.collected} dias coletados (Semana ${12 - week.weekOffset})`}>
              <div
                className={getBarColor(week.collected)} style={{ width: '100%', height: `${heightPct}%`, borderRadius: '4px 4px 0 0', opacity: 0.8, transition: 'opacity 0.2s' }}></div>
            </div>
          );
        })}
      </div>

      <div className="text-muted" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginTop: '0.5rem' }}>
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

  const years: { year: number; days: string[]; start: Date }[] = [];
  const currentYear = start.getUTCFullYear();
  const endYear = end.getUTCFullYear();

  for (let yr = currentYear; yr <= endYear; yr++) {
    const yearDays: string[] = [];
    const yrStart = new Date(Date.UTC(yr, 0, 1));
    const yrEnd = new Date(Date.UTC(yr, 11, 31));

    const actualStart = new Date(Math.max(yrStart.getTime(), start.getTime()));
    const actualEnd = new Date(Math.min(yrEnd.getTime(), end.getTime()));

    const curr = new Date(actualStart);
    while (curr <= actualEnd) {
      yearDays.push(toDateString(curr));
      curr.setUTCDate(curr.getUTCDate() + 1);
    }

    if (yearDays.length> 0) {
      years.push({ year: yr, days: yearDays, start: actualStart });
    }
  }

  const allDays = years.flatMap(y => y.days);
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
    return isFocused ? `${base} heatmap-focused` : base;
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
      case 'ArrowUp': newIndex = Math.max(0, currentIndex - 1); e.preventDefault(); break;
      case 'ArrowDown': newIndex = Math.min(allDays.length - 1, currentIndex + 1); e.preventDefault(); break;
      case 'ArrowLeft': newIndex = Math.max(0, currentIndex - 7); e.preventDefault(); break;
      case 'ArrowRight': newIndex = Math.min(allDays.length - 1, currentIndex + 7); e.preventDefault(); break;
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {years.map(({ year, days: yDays, start: yrStart }) => {
        const startDayOfWeek = yrStart.getUTCDay();
        const paddedDays: (string | null)[] = Array(startDayOfWeek).fill(null).concat(yDays);
        const yrWeeks: (string | null)[][] = [];
        for (let i = 0; i < paddedDays.length; i += 7) { yrWeeks.push(paddedDays.slice(i, i + 7)); }
        return (
          <div key={year}>
            <h4 style={{ marginBottom: '1rem', fontSize: '1.25rem' }}>{year}</h4>
            <div style={{ display: 'flex', gap: '4px', overflowX: 'auto', paddingBottom: '1rem' }} role="grid" aria-label={`Activity heatmap for ${tribunalName} in ${year}.`} tabIndex={0} onKeyDown={handleGridKeyDown} onFocus={() => { if (!focusedCell) setFocusedCell(allDays[allDays.length - 1]); }} onBlur={() => { setFocusedCell(null); setHoveredCell(null); }}>
              <div aria-hidden="true" style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '20px', paddingRight: '0.5rem', fontSize: '0.75rem', color: 'var(--pico-muted-color)' }}>
                <div style={{ height: '14px' }}></div>
                <div style={{ height: '14px', lineHeight: '14px' }}>Seg</div>
                <div style={{ height: '14px' }}></div>
                <div style={{ height: '14px', lineHeight: '14px' }}>Qua</div>
                <div style={{ height: '14px' }}></div>
                <div style={{ height: '14px', lineHeight: '14px' }}>Sex</div>
                <div style={{ height: '14px' }}></div>
              </div>
              {yrWeeks.map((week, weekIndex) => (
                <div key={`w-${year}-${weekIndex}`} role="row" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ height: '16px', fontSize: '0.75rem', color: 'var(--pico-muted-color)', marginBottom: '4px' }}>
                    {week.some(d => d && d.endsWith("-01")) ? new Date(week.find(d => d && d.endsWith("-01"))! + "T00:00:00Z").toLocaleString('pt-BR', { month: 'short' }) : ''}
                  </div>
                  {week.map((day, dayIndex) => (
                    <div
                      key={day || `empty-${year}-${weekIndex}-${dayIndex}`}
                      id={day ? `cell-${day}` : undefined}
                      role="gridcell"
                      className={getCellColor(day) || undefined}
                      style={{
                        width: '14px',
                        height: '14px',
                        borderRadius: '2px',
                        cursor: day && getCellStatus(day) === 'collected' && baseUrl ? 'pointer' : 'default',
                        backgroundColor: !day ? 'transparent' : undefined // Fallback for null days
                      }}
                      aria-label={getAriaLabel(day)}
                      aria-selected={focusedCell === day}
                      onMouseEnter={(e: any) => handleCellInteraction(e, day, 'enter')}
                      onMouseMove={(e: any) => handleCellInteraction(e, day, 'move')}
                      onMouseLeave={(e: any) => handleCellInteraction(e, day, 'leave')}
                      onTouchStart={(e: any) => handleCellInteraction(e, day, 'touch')}
                      onClick={(e: any) => { handleCellInteraction(e, day, 'click'); setFocusedCell(day); }}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>
        );
      })}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--pico-muted-border-color)', fontSize: '0.875rem' }}>
        <span className="text-muted">
          <strong>{coveredDays}</strong> de <strong>{totalDays}</strong> dias com dados
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span className="text-muted" style={{ marginRight: '0.5rem' }}>Legenda:</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div className="heatmap-missing" style={{ width: '14px', height: '14px', borderRadius: '2px' }}></div>
            <span>Faltante</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div className="heatmap-absent" style={{ width: '14px', height: '14px', borderRadius: '2px' }}></div>
            <span>Ausente</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div className="heatmap-collected" style={{ width: '14px', height: '14px', borderRadius: '2px' }}></div>
            <span>Coletado</span>
          </div>
        </div>
      </div>

      {velocityMetrics && velocityMetrics.hasEnoughHistory && (
        <div style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid var(--pico-muted-border-color)' }}>
          <VelocityTimeline metrics={velocityMetrics} />
        </div>
      )}

      {hoveredCell && <CellTooltip cellData={hoveredCell.data} position={hoveredCell.position} />}
    </div>
  );
}
