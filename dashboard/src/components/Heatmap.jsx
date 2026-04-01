import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { CellTooltip } from './CellTooltip';

export function calculateVelocityAndRegression(coverageSet, targetRangeEndStr, tribunalStartDateStr) {
  if (!tribunalStartDateStr) return null;

  const targetRangeEnd = new Date(targetRangeEndStr + "T00:00:00Z");
  const tribunalStartDate = new Date(tribunalStartDateStr + "T00:00:00Z");

  if (targetRangeEnd < tribunalStartDate) return null;

  const MS_PER_DAY = 1000 * 60 * 60 * 24;

  let totalHistoricalDays = 0;
  let totalHistoricalCollected = 0;

  let current30Days = 0;
  let current30Collected = 0;
  let baseline60Days = 0;
  let baseline60Collected = 0;

  let current = new Date(tribunalStartDate);
  while (current <= targetRangeEnd) {
    totalHistoricalDays++;
    const dStr = current.toISOString().split('T')[0];
    const isCollected = coverageSet.has(dStr);

    if (isCollected) {
      totalHistoricalCollected++;
    }

    const diffDays = Math.floor((targetRangeEnd - current) / MS_PER_DAY);
    if (diffDays < 30) {
      current30Days++;
      if (isCollected) current30Collected++;
    } else if (diffDays < 90) {
      baseline60Days++;
      if (isCollected) baseline60Collected++;
    }
    current.setUTCDate(current.getUTCDate() + 1);
  }

  const weeklyData = [];
  let recent4WeeksCollected = 0;

  for (let w = 11; w >= 0; w--) {
    let weekCollected = 0;

    const weekEnd = new Date(targetRangeEnd.getTime() - w * 7 * MS_PER_DAY);
    const weekStart = new Date(weekEnd.getTime() - 6 * MS_PER_DAY);

    let day = new Date(weekStart);
    while (day <= weekEnd) {
      if (day >= tribunalStartDate) {
        const dStr = day.toISOString().split('T')[0];
        if (coverageSet.has(dStr)) weekCollected++;
      }
      day.setUTCDate(day.getUTCDate() + 1);
    }

    weeklyData.push({
      weekOffset: w,
      collected: weekCollected,
    });

    if (w < 4) {
      recent4WeeksCollected += weekCollected;
    }
  }

  const historicalAvgVelocity = (totalHistoricalCollected / totalHistoricalDays) * 7;
  const currentVelocity = recent4WeeksCollected / 4;

  let baselineCoverage = baseline60Days > 0 ? baseline60Collected / baseline60Days : 0;
  let currentCoverage = 0;
  if (current30Days > 0) currentCoverage = current30Collected / current30Days;

  let trend = 0;
  if (historicalAvgVelocity > 0) {
    trend = ((currentVelocity - historicalAvgVelocity) / historicalAvgVelocity) * 100;
  } else if (currentVelocity > 0) {
    trend = 100;
  }

  let regressionDrop = 0;
  if (baselineCoverage > 0) {
    regressionDrop = ((baselineCoverage - currentCoverage) / baselineCoverage) * 100;
  }

  return {
    weeklyData,
    historicalAvgVelocity,
    currentVelocity,
    trend,
    baselineCoverage: baselineCoverage * 100,
    currentCoverage: currentCoverage * 100,
    regressionDrop,
    hasEnoughHistory: totalHistoricalDays >= 10
  };
}

export function VelocityTimeline({ metrics }) {
  if (!metrics || !metrics.hasEnoughHistory) return null;

  const { weeklyData, historicalAvgVelocity, currentVelocity, trend } = metrics;
  const maxCollected = Math.max(7, ...weeklyData.map(w => w.collected));

  let trendColor = "text-gray-500 dark:text-gray-400";
  let trendText = "Stable";
  if (currentVelocity > historicalAvgVelocity * 1.2) {
    trendColor = "text-success";
    trendText = "Accelerating";
  } else if (currentVelocity < historicalAvgVelocity * 0.7) {
    trendColor = "text-danger";
    trendText = "Declining";
  }

  const getBarColor = (collected) => {
    if (collected === 0) return "bg-danger";
    if (collected < 4) return "bg-warning";
    return "bg-success";
  };

  return (
    <div className="mt-6 border-t border-gray-100 dark:border-slate-800 pt-4" aria-label="Velocity Timeline">
      <div className="flex justify-between items-end mb-3">
        <div>
          <h4 className="text-sm font-medium text-black dark:text-white">Velocity Timeline</h4>
          <p className="text-xs text-gray-500 dark:text-gray-400">Last 12 weeks collection rate</p>
        </div>
        <div className="text-right">
          <div className="text-sm font-mono text-black dark:text-white">{currentVelocity.toFixed(1)} docs/wk avg</div>
          <div className={`text-xs ${trendColor}`}>
            {trend > 0 ? '+' : ''}{trend.toFixed(0)}% vs avg ({trendText})
          </div>
        </div>
      </div>

      <div className="flex items-end gap-1 h-16 w-full mt-2" role="list">
        {weeklyData.map((week, idx) => {
          const heightPct = Math.max(5, (week.collected / maxCollected) * 100);

          return (
            <div
              key={`w-${idx}`}
              className="group relative flex-1 flex flex-col justify-end h-full"
              role="listitem"
            >
              <div
                className={`w-full rounded-t-sm opacity-80 group-hover:opacity-100 transition-opacity ${getBarColor(week.collected)}`}
                style={{ height: `${heightPct}%` }}
              ></div>
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10 w-max bg-slate-900 text-white text-xs rounded py-1 px-2 shadow-lg">
                <div className="font-mono text-center">{week.collected} days collected</div>
                <div className="text-[10px] text-gray-300 text-center opacity-80 mt-0.5">Week {12 - week.weekOffset}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex justify-between text-[10px] text-gray-400 mt-1 uppercase font-mono tracking-wider">
        <span>12 wks ago</span>
        <span>Current</span>
      </div>
    </div>
  );
}

export function Heatmap({ globalStartDateStr, globalEndDateStr, tribunalStartDateStr, coverageSet, tribunalName, baseUrl, velocityMetrics }) {
  const [hoveredCell, setHoveredCell] = useState(null);
  const [focusedCell, setFocusedCell] = useState(null);

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

  if (start > end) {
    return <div className="text-gray-600 dark:text-gray-300 p-4">Invalid date range.</div>;
  }

  const years = [];
  let currentYear = start.getUTCFullYear();
  const endYear = end.getUTCFullYear();

  for (let yr = currentYear; yr <= endYear; yr++) {
    const yearDays = [];
    const yrStart = new Date(Date.UTC(yr, 0, 1));
    const yrEnd = new Date(Date.UTC(yr, 11, 31));

    const actualStart = new Date(Math.max(yrStart, start));
    const actualEnd = new Date(Math.min(yrEnd, end));

    let curr = new Date(actualStart);
    while (curr <= actualEnd) {
      yearDays.push(curr.toISOString().split('T')[0]);
      curr.setUTCDate(curr.getUTCDate() + 1);
    }

    if (yearDays.length > 0) {
      years.push({ year: yr, days: yearDays, start: actualStart });
    }
  }

  const allDays = years.flatMap(y => y.days);
  const coveredDays = allDays.filter(d => coverageSet.has(d)).length;
  const totalDays = allDays.length;

  const getCellStatus = (dateStr) => {
    if (tribunalStartDateStr && dateStr < tribunalStartDateStr) {
      return 'outside';
    }
    if (coverageSet.has(dateStr)) return 'collected';
    if (velocityMetrics?.absentSet?.has(dateStr)) return 'absent';
    return 'missing';
  };

  const getCellColor = (dateStr) => {
    if (!dateStr) return "bg-transparent";
    const status = getCellStatus(dateStr);
    const base = status === 'outside' ? "bg-gray-50 dark:bg-slate-800 hover:bg-border opacity-30" :
                 status === 'collected' ? "bg-success hover:bg-success-hover shadow-[inset_0_0_10px_rgba(255,255,255,0.1)]" :
                 status === 'absent' ? "bg-warning hover:bg-warning-hover opacity-80" :
                 "bg-danger hover:bg-danger-hover";
    const isFocused = focusedCell === dateStr;
    const focusClasses = isFocused ? "ring-2 ring-accent ring-offset-1 dark:ring-offset-slate-950 z-10 scale-110" : "";
    return clsx(base, focusClasses);
  };

  const getAriaLabel = (dateStr) => {
    if (!dateStr) return "Empty cell";
    const status = getCellStatus(dateStr);
    if (status === 'outside') return `${dateStr}: Before Tribunal Joined`;
    if (status === 'absent') return `${dateStr}: Confirmed Absent (No journal published)`;
    return `${dateStr}: ${status === 'collected' ? 'Collected' : 'Missing'}`;
  };

  const handleCellInteraction = (e, dateStr, type) => {
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
        window.location.href = `${baseUrl}monitor/${tribunalName.toLowerCase()}/${dateStr}`;
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

  const handleGridKeyDown = (e) => {
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
    <div className="flex flex-col gap-8 min-w-max pb-8">
      {years.map(({ year, days: yDays, start: yrStart }) => {
        const startDayOfWeek = yrStart.getUTCDay();
        const paddedDays = Array(startDayOfWeek).fill(null).concat(yDays);
        const yrWeeks = [];
        for (let i = 0; i < paddedDays.length; i += 7) { yrWeeks.push(paddedDays.slice(i, i + 7)); }
        return (
          <div key={year} className="flex flex-col gap-2">
            <h4 className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-widest font-mono">Year {year}</h4>
            <div className="flex gap-1 outline-none" role="grid" aria-label={`Activity heatmap for ${tribunalName} in ${year}.`} tabIndex={0} onKeyDown={handleGridKeyDown} onFocus={() => { if (!focusedCell) setFocusedCell(allDays[allDays.length - 1]); }} onBlur={() => { setFocusedCell(null); setHoveredCell(null); }}>
              <div className="flex flex-col gap-1 flex-shrink-0 text-[10px] text-gray-500 dark:text-gray-400 font-mono pt-1 mr-2 justify-between h-[104px]" aria-hidden="true">
                <div className="h-3"></div><div className="h-3 leading-3">Mon</div><div className="h-3"></div><div className="h-3 leading-3">Wed</div><div className="h-3"></div><div className="h-3 leading-3">Fri</div><div className="h-3"></div>
              </div>
              {yrWeeks.map((week, weekIndex) => (
                <div key={`w-${year}-${weekIndex}`} className="flex flex-col gap-1 flex-shrink-0" role="row">
                  <div className="h-3 mb-1 text-[9px] text-gray-400 overflow-visible whitespace-nowrap font-mono uppercase tracking-tighter">
                    {week.some(d => d && d.endsWith("-01")) ? new Date(week.find(d => d && d.endsWith("-01")) + "T00:00:00Z").toLocaleString('en-US', { month: 'short' }) : ''}
                  </div>
                  {week.map((day, dayIndex) => (
                    <div key={day || `empty-${year}-${weekIndex}-${dayIndex}`} id={day ? `cell-${day}` : undefined} role="gridcell" className={clsx("w-3 h-3 rounded-sm transition-colors duration-200 opacity-80 hover:opacity-100", day ? "cursor-pointer" : "cursor-default", getCellColor(day))} aria-label={getAriaLabel(day)} aria-selected={focusedCell === day} onMouseEnter={(e) => handleCellInteraction(e, day, 'enter')} onMouseMove={(e) => handleCellInteraction(e, day, 'move')} onMouseLeave={(e) => handleCellInteraction(e, day, 'leave')} onTouchStart={(e) => handleCellInteraction(e, day, 'touch')} onClick={(e) => { handleCellInteraction(e, day, 'click'); setFocusedCell(day); }} />
                  ))}
                </div>
              ))}
            </div>
          </div>
        );
      })}
      <div className="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
        <span>{coveredDays} / {totalDays} days collected</span>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-danger opacity-80"></div><span>Missing</span></div>
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-warning opacity-80"></div><span>Absent</span></div>
          <div className="flex items-center gap-1"><div className="w-3 h-3 rounded-sm bg-success opacity-80"></div><span>Collected</span></div>
        </div>
      </div>
      <VelocityTimeline metrics={velocityMetrics} />
      {hoveredCell && <CellTooltip cellData={hoveredCell.data} position={hoveredCell.position} />}
    </div>
  );
}
