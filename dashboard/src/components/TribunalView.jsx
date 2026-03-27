import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';
import { CellTooltip } from './CellTooltip';
import { FilterPanel } from './TribunalFilters/FilterPanel';
import { BatchDownload } from './TribunalFilters/BatchDownload';

const TRIBUNALS = [
  "STF", "STJ", "TST", "TSE", "STM", "CNJ",
  "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
  "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7", "TRT8", "TRT9", "TRT10", "TRT11", "TRT12", "TRT13", "TRT14", "TRT15", "TRT16", "TRT17", "TRT18", "TRT19", "TRT20", "TRT21", "TRT22", "TRT23", "TRT24",
  "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT", "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA", "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO", "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJTO",
  "TRE-AC", "TRE-AL", "TRE-AM", "TRE-AP", "TRE-BA", "TRE-CE", "TRE-DF", "TRE-ES", "TRE-GO", "TRE-MA", "TRE-MG", "TRE-MS", "TRE-MT", "TRE-PA", "TRE-PB", "TRE-PE", "TRE-PI", "TRE-PR", "TRE-RJ", "TRE-RN", "TRE-RO", "TRE-RR", "TRE-RS", "TRE-SC", "TRE-SE", "TRE-SP", "TRE-TO"
];

export function TribunalView({ initialCoverage, initialEtas, initialTargetRange, initialStartDates }) {
  const { data: allData } = useDataRefresh(null, null);

  // Default filter state
  const defaultFilters = {
    dateRange: { start: '', end: '' }, // empty means use targetRange
    coverageRange: [0, 100],
    gapPattern: false,
    velocityTrend: 'all',
    status: 'all' // active | inactive
  };

  const [filters, setFilters] = useState(defaultFilters);
  const [isHydrated, setIsHydrated] = useState(false);
  const [selectedTribunals, setSelectedTribunals] = useState(new Set());

  // Load from localStorage on client mount only to prevent hydration mismatch
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('causaganha-filters');
      if (saved) {
        try {
          setFilters(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse saved filters", e);
        }
      }
      setIsHydrated(true);
    }
  }, []);

  // Persist filters when they change
  useEffect(() => {
    if (isHydrated && typeof window !== 'undefined') {
      localStorage.setItem('causaganha-filters', JSON.stringify(filters));
    }
  }, [filters, isHydrated]);

  // Prefer fresh client-side data, fall back to build-time props
  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const targetRange = allData?.targetRange ?? initialTargetRange ?? { start: "2024-01-01", end: "2026-02-03" };
  const startDates = allData?.tribunalStartDates ?? initialStartDates;

  const isStartDatesLoading = !startDates;
  const safeStartDates = startDates || {};

  // Apply filters to TRIBUNALS
  const filteredTribunals = TRIBUNALS.filter(t => {
    const tCoverage = new Set(coverage[t] || []);
    const tEta = etas[t] || { missing_days: null, velocity_14d: 0, eta_days: null };
    const tStartStr = safeStartDates[t];

    // Determine the effective date range based on filters and targetRange
    const effectiveStartStr = filters.dateRange.start || targetRange.start;
    const effectiveEndStr = filters.dateRange.end || targetRange.end;

    // We only count days from the LATEST of (tribunal start date, effective start date)
    const startObj = new Date(Math.max(
      new Date((tStartStr || targetRange.start) + "T00:00:00Z"),
      new Date(effectiveStartStr + "T00:00:00Z")
    ));
    const endObj = new Date(effectiveEndStr + "T00:00:00Z");

    let expectedInFilter = 0;
    let missingInFilter = 0;
    let maxContinuousGap = 0;
    let currentGap = 0;

    if (startObj <= endObj) {
      expectedInFilter = Math.floor((endObj - startObj) / (1000 * 60 * 60 * 24)) + 1;

      // Iterate through the dates to count missing and find >7 days gaps
      let current = new Date(startObj);
      while (current <= endObj) {
        const dateStr = current.toISOString().split('T')[0];
        if (!tCoverage.has(dateStr)) {
          missingInFilter++;
          currentGap++;
          if (currentGap > maxContinuousGap) {
            maxContinuousGap = currentGap;
          }
        } else {
          currentGap = 0;
        }
        current.setUTCDate(current.getUTCDate() + 1);
      }
    }

    const coveragePct = expectedInFilter > 0 ? ((expectedInFilter - missingInFilter) / expectedInFilter) * 100 : 0;

    // Coverage Range
    if (coveragePct < filters.coverageRange[0] || coveragePct > filters.coverageRange[1]) return false;

    // Status
    // Active means velocity > 0 AND there's missing data (they are actively working).
    // Inactive means velocity = 0 AND there's missing data (stalled).
    // If missing == 0, it's neither active nor inactive, it's complete. We'll exclude complete from active/inactive filters unless 'all' is chosen.
    const isComplete = missingInFilter === 0;
    if (filters.status === 'active' && (tEta.velocity_14d === 0 || isComplete)) return false;
    if (filters.status === 'inactive' && (tEta.velocity_14d > 0 || isComplete)) return false;

    // Velocity Trend
    // We only have velocity_14d right now. Let's use it as a proxy for now, but a proper trend needs historical velocity.
    // If 'all', pass. Otherwise, we do basic heuristics or skip if we lack data.
    if (filters.velocityTrend !== 'all') {
       if (filters.velocityTrend === 'stable' && tEta.velocity_14d === 0) return false;
       if (filters.velocityTrend === 'accelerating' && tEta.velocity_14d < 10) return false; // dummy heuristic since we don't have trend data
       if (filters.velocityTrend === 'decelerating' && tEta.velocity_14d > 0 && tEta.velocity_14d < 10) return false;
    }

    // Gap Pattern (> 7 days gap)
    if (filters.gapPattern && maxContinuousGap <= 7) {
       return false;
    }

    return true;
  });

  const handleToggleSelectAll = (e) => {
    if (e.target.checked) {
      const allFiltered = new Set(filteredTribunals);
      setSelectedTribunals(allFiltered);
    } else {
      setSelectedTribunals(new Set());
    }
  };

  const handleToggleSelect = (t) => {
    const nextSet = new Set(selectedTribunals);
    if (nextSet.has(t)) {
      nextSet.delete(t);
    } else {
      nextSet.add(t);
    }
    setSelectedTribunals(nextSet);
  };

  return (
    <div className="flex flex-col gap-6">
      <FilterPanel
        filters={filters}
        setFilters={setFilters}
        filteredCount={filteredTribunals.length}
        totalCount={TRIBUNALS.length}
      />

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 card p-4">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer font-medium text-black dark:text-white text-sm">
            <input
              type="checkbox"
              className="rounded border-gray-300 text-accent focus:ring-accent w-4 h-4 cursor-pointer"
              checked={filteredTribunals.length > 0 && selectedTribunals.size === filteredTribunals.length}
              onChange={handleToggleSelectAll}
            />
            Selecionar todos os {filteredTribunals.length}
          </label>
        </div>

        <BatchDownload
          selectedTribunals={selectedTribunals}
          filteredTribunals={filteredTribunals}
          allData={allData}
          initialCoverage={initialCoverage}
          initialStartDates={initialStartDates}
          targetRange={targetRange}
        />
      </div>

      <div className="grid grid-cols-1 gap-6">
        {filteredTribunals.length === 0 ? (
          <div className="card p-8 text-center text-gray-500 dark:text-gray-400">
            Nenhum tribunal corresponde aos filtros selecionados.
          </div>
        ) : (
          filteredTribunals.map(t => {
            const tCoverage = new Set(coverage[t] || []);
            const tEta = etas[t] || { missing_days: null, velocity_14d: 0, eta_days: null };
            const tStartStr = safeStartDates[t];

          let tExpected = 0;
          if (tStartStr) {
            const start = new Date(tStartStr + "T00:00:00Z");
            const end = new Date(targetRange.end + "T00:00:00Z");
            if (start <= end) {
              tExpected = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
            }
          }

            const tMissing = tEta.missing_days !== null ? tEta.missing_days : Math.max(0, tExpected - tCoverage.size);

            let etaText = "Pending";
            if (tMissing === 0 && tExpected > 0) {
              etaText = "Complete ✓";
            } else if (tEta.eta_days) {
              if (tEta.eta_days < 30) {
                etaText = `~${tEta.eta_days} days`;
              } else {
                const months = Math.round(tEta.eta_days / 30);
                etaText = `~${months} month${months > 1 ? 's' : ''}`;
              }
            }

            const statusColor = (tMissing === 0 && tExpected > 0) ? "text-success" : "text-warning";
            const isSelected = selectedTribunals.has(t);

            return (
              <div key={t} className={`card flex flex-col lg:flex-row gap-6 p-4 border-l-4 transition-colors ${isSelected ? 'border-l-accent bg-accent/5' : 'border-l-transparent'}`}>

                {/* Sidebar: Checkbox and Details */}
                <div className="w-full lg:w-64 flex flex-col gap-4 flex-shrink-0">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 font-semibold text-lg text-black dark:text-white cursor-pointer">
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-accent focus:ring-accent w-4 h-4 cursor-pointer"
                        checked={isSelected}
                        onChange={() => handleToggleSelect(t)}
                      />
                      {t}
                    </label>
                  </div>

                  <div className="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-100 dark:border-slate-800">
                    <div className="text-sm flex justify-between">
                      <span className="text-gray-600 dark:text-gray-300">Start Date</span>
                      <span className="font-mono text-black dark:text-white">
                        {isStartDatesLoading ? (
                          <span className="text-gray-500 dark:text-gray-400 italic">Pending...</span>
                        ) : (
                          tStartStr || "Unknown"
                        )}
                      </span>
                    </div>

                    <div className="text-sm flex justify-between">
                      <span className="text-gray-600 dark:text-gray-300">Status</span>
                      <span className={`font-medium ${statusColor}`}>{etaText}</span>
                    </div>

                    <div className="text-sm flex justify-between">
                      <span className="text-gray-600 dark:text-gray-300">Missing</span>
                      <span className="font-mono text-black dark:text-white">
                        {isStartDatesLoading ? "..." : `${tMissing} days`}
                      </span>
                    </div>

                    {tEta.velocity_14d > 0 && (
                      <div className="text-sm flex justify-between">
                        <span className="text-gray-600 dark:text-gray-300">Velocity</span>
                        <span className="font-mono text-black dark:text-white">{tEta.velocity_14d.toFixed(1)} docs/day</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Main: Heatmap area */}
                <div className="flex-1 overflow-x-auto custom-scrollbar pb-4">
                  <Heatmap
                    globalStartDateStr={targetRange.start}
                    globalEndDateStr={targetRange.end}
                    tribunalStartDateStr={tStartStr}
                    coverageSet={tCoverage}
                    tribunalName={t}
                  />
                </div>

              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// Sub-component for the multi-year heatmap
function Heatmap({ globalStartDateStr, globalEndDateStr, tribunalStartDateStr, coverageSet, tribunalName }) {
  const [hoveredCell, setHoveredCell] = useState(null);

  // Close tooltip if tapping outside
  useEffect(() => {
    const handleOutsideInteraction = () => setHoveredCell(null);
    // document might be undefined in SSR
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

  // Generate all days in the global backfill range
  const start = new Date(globalStartDateStr + "T00:00:00Z");
  const end = new Date(globalEndDateStr + "T00:00:00Z");
  const days = [];

  // Protect against bad data
  if (start > end) {
    return <div className="text-gray-600 dark:text-gray-300 p-4">Invalid date range.</div>;
  }

  let current = new Date(start);
  while (current <= end) {
    const dStr = current.toISOString().split('T')[0];
    days.push(dStr);
    current.setUTCDate(current.getUTCDate() + 1);
  }

  // Group by week (start on Monday for better spacing, or Sunday to match typical calendars)
  // Let's pad to start on Sunday
  const startDayOfWeek = start.getUTCDay();
  const paddedDays = Array(startDayOfWeek).fill(null).concat(days);

  const weeks = [];
  for (let i = 0; i < paddedDays.length; i += 7) {
    weeks.push(paddedDays.slice(i, i + 7));
  }

  const getCellStatus = (dateStr) => {
    if (tribunalStartDateStr && dateStr < tribunalStartDateStr) {
      return 'outside';
    }
    return coverageSet.has(dateStr) ? 'collected' : 'missing';
  };

  const getCellColor = (dateStr) => {
    if (!dateStr) return "bg-transparent"; // padding cell

    const status = getCellStatus(dateStr);
    if (status === 'outside') return "bg-gray-50 dark:bg-slate-800 hover:bg-border"; // Gray cell
    if (status === 'collected') return "bg-success hover:bg-success-hover"; // Green cell
    return "bg-danger hover:bg-danger-hover"; // Red cell
  };

  const getAriaLabel = (dateStr) => {
    if (!dateStr) return "Empty cell";
    const status = getCellStatus(dateStr);
    if (status === 'outside') return `${dateStr}: Before Tribunal Joined`;
    return `${dateStr}: ${status === 'collected' ? 'Collected' : 'Missing'}`;
  };

  const handleCellInteraction = (e, dateStr, type) => {
    e.stopPropagation(); // prevent document listener from closing tooltip immediately
    if (!dateStr) return;

    if (type === 'leave') {
      setHoveredCell(null);
      return;
    }

    // Handle touch interactions to prevent simulated clicks from firing immediately after touch
    if (type === 'touch') {
      // Prevent default to stop the subsequent simulated click event
      if (e.cancelable) e.preventDefault();

      const pos = { x: e.touches[0].clientX, y: e.touches[0].clientY };

      if (hoveredCell?.data?.date === dateStr) {
        // Second touch on the same cell hides tooltip
        setHoveredCell(null);
      } else {
        setHoveredCell({
          data: {
            date: dateStr,
            status: getCellStatus(dateStr),
            uploadedAt: null,
            sizeMb: null
          },
          position: pos
        });
      }
      return;
    }

    const pos = { x: e.clientX, y: e.clientY };

    // For click, we want to toggle similar to touch if it's the same cell
    if (type === 'click' && hoveredCell?.data?.date === dateStr) {
      setHoveredCell(null);
      return;
    }

    setHoveredCell({
      data: {
        date: dateStr,
        status: getCellStatus(dateStr),
        // placeholder for potentially added backend fields
        uploadedAt: null,
        sizeMb: null
      },
      position: pos
    });
  };

  const coveredDays = days.filter(d => coverageSet.has(d)).length;
  const totalDays = days.length;

  return (
    <div className="flex flex-col gap-4 min-w-max">

      <div className="flex gap-1" role="grid" aria-label={`Activity heatmap for ${tribunalName}`}>
        {/* Weekday labels */}
        <div className="flex flex-col gap-1 flex-shrink-0 text-[10px] text-gray-500 dark:text-gray-400 font-mono pt-1 mr-2 justify-between h-[104px]">
          <div className="h-3" aria-hidden="true"></div>
          <div className="h-3 leading-3" aria-hidden="true">Mon</div>
          <div className="h-3" aria-hidden="true"></div>
          <div className="h-3 leading-3" aria-hidden="true">Wed</div>
          <div className="h-3" aria-hidden="true"></div>
          <div className="h-3 leading-3" aria-hidden="true">Fri</div>
          <div className="h-3" aria-hidden="true"></div>
        </div>

        {weeks.map((week, weekIndex) => (
          <div key={`w-${weekIndex}`} className="flex flex-col gap-1 flex-shrink-0" role="row">
            {week.map((day, dayIndex) => (
              <div
                key={day || `empty-${weekIndex}-${dayIndex}`}
                role="gridcell"
                className={clsx(
                  "w-3 h-3 rounded-sm transition-colors duration-200 opacity-80 hover:opacity-100",
                  day ? "cursor-pointer" : "cursor-default",
                  getCellColor(day)
                )}
                aria-label={getAriaLabel(day)}
                onMouseEnter={(e) => handleCellInteraction(e, day, 'enter')}
                onMouseMove={(e) => handleCellInteraction(e, day, 'move')}
                onMouseLeave={(e) => handleCellInteraction(e, day, 'leave')}
                onTouchStart={(e) => handleCellInteraction(e, day, 'touch')}
                onClick={(e) => {
                  e.stopPropagation();
                  handleCellInteraction(e, day, 'click');
                }}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center text-xs text-gray-500 dark:text-gray-400">
        <span>{coveredDays} / {totalDays} days collected</span>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-danger opacity-80"></div>
            <span>Missing</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-success opacity-80"></div>
            <span>Collected</span>
          </div>
        </div>
      </div>

      {hoveredCell && (
        <CellTooltip
          cellData={hoveredCell.data}
          position={hoveredCell.position}
        />
      )}

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--color-border);
          border-radius: 4px;
        }
        .custom-scrollbar:hover::-webkit-scrollbar-thumb {
          background: var(--color-content-tertiary);
        }
      `}</style>
    </div>
  );
}
