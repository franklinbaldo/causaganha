import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';
import { CellTooltip } from './CellTooltip';

const TRIBUNALS = [
  "STF", "STJ", "TST", "TSE", "STM", "CNJ",
  "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
  "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7", "TRT8", "TRT9", "TRT10", "TRT11", "TRT12", "TRT13", "TRT14", "TRT15", "TRT16", "TRT17", "TRT18", "TRT19", "TRT20", "TRT21", "TRT22", "TRT23", "TRT24",
  "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT", "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA", "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO", "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJTO",
  "TRE-AC", "TRE-AL", "TRE-AM", "TRE-AP", "TRE-BA", "TRE-CE", "TRE-DF", "TRE-ES", "TRE-GO", "TRE-MA", "TRE-MG", "TRE-MS", "TRE-MT", "TRE-PA", "TRE-PB", "TRE-PE", "TRE-PI", "TRE-PR", "TRE-RJ", "TRE-RN", "TRE-RO", "TRE-RR", "TRE-RS", "TRE-SC", "TRE-SE", "TRE-SP", "TRE-TO"
];

export function TribunalView({ initialCoverage, initialEtas, initialTargetRange, initialStartDates }) {
  const { data: allData } = useDataRefresh(null, null);
  const [selectedTribunal, setSelectedTribunal] = useState("STF");

  // Prefer fresh client-side data, fall back to build-time props
  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const targetRange = allData?.targetRange ?? initialTargetRange ?? { start: "2024-01-01", end: "2026-02-03" };
  const startDates = allData?.tribunalStartDates ?? initialStartDates;

  const selectedCoverage = new Set(coverage[selectedTribunal] || []);
  const selectedEtaData = etas[selectedTribunal] || { missing_days: null, velocity_14d: 0, eta_days: null };

  const isStartDatesLoading = !startDates;
  const safeStartDates = startDates || {};
  const tribunalStartDate = safeStartDates[selectedTribunal];

  // Calculate total days expected for this tribunal
  let expectedDays = 0;
  if (tribunalStartDate) {
    const start = new Date(tribunalStartDate + "T00:00:00Z");
    const end = new Date(targetRange.end + "T00:00:00Z");
    if (start <= end) {
      expectedDays = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
    }
  }

  // Calculate actual missing days if not provided
  const actualMissingDays = selectedEtaData.missing_days !== null
    ? selectedEtaData.missing_days
    : Math.max(0, expectedDays - selectedCoverage.size);

  // Render text ETA
  let etaText = "Pending";
  if (actualMissingDays === 0 && expectedDays > 0) {
    etaText = "Complete ✓";
  } else if (selectedEtaData.eta_days) {
    if (selectedEtaData.eta_days < 30) {
      etaText = `~${selectedEtaData.eta_days} days`;
    } else {
      const months = Math.round(selectedEtaData.eta_days / 30);
      etaText = `~${months} month${months > 1 ? 's' : ''}`;
    }
  }

  const statusColor = (actualMissingDays === 0 && expectedDays > 0) ? "text-success" : "text-warning";

  return (
    <div className="flex flex-col gap-6">
      <div className="card p-4 flex flex-col lg:flex-row gap-6">

        {/* Sidebar: Dropdown and Details */}
        <div className="w-full lg:w-64 flex flex-col gap-4 flex-shrink-0">
          <div>
            <label htmlFor="tribunal-select" className="block text-sm font-medium text-black dark:text-white mb-2">
              Select Tribunal
            </label>
            <select
              id="tribunal-select"
              value={selectedTribunal}
              onChange={(e) => setSelectedTribunal(e.target.value)}
              className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-black dark:text-white focus:outline-none focus:border-accent"
            >
              {TRIBUNALS.map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-100 dark:border-slate-800">
            <h3 className="text-lg font-semibold text-black dark:text-white">{selectedTribunal}</h3>

            <div className="text-sm flex justify-between">
              <span className="text-gray-600 dark:text-gray-300">Start Date</span>
              <span className="font-mono text-black dark:text-white">
                {isStartDatesLoading ? (
                  <span className="text-gray-500 dark:text-gray-400 italic">Pending...</span>
                ) : (
                  tribunalStartDate || "Unknown"
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
                {isStartDatesLoading ? "..." : `${actualMissingDays} days`}
              </span>
            </div>

            {selectedEtaData.velocity_14d > 0 && (
              <div className="text-sm flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">Velocity</span>
                <span className="font-mono text-black dark:text-white">{selectedEtaData.velocity_14d.toFixed(1)} docs/day</span>
              </div>
            )}

            <div className="text-sm flex justify-between mt-2 pt-2 border-t border-gray-100 dark:border-slate-800">
               <span className="text-gray-600 dark:text-gray-300">Last Updated</span>
               <span className="font-mono text-xs text-gray-500 dark:text-gray-400">
                 {allData?.backfillProgress?.last_updated ? new Date(allData.backfillProgress.last_updated).toLocaleDateString() : 'Never'}
               </span>
            </div>
          </div>
        </div>

        {/* Main: Heatmap area */}
        <div className="flex-1 overflow-x-auto custom-scrollbar pb-4">
          <Heatmap
            globalStartDateStr={targetRange.start}
            globalEndDateStr={targetRange.end}
            tribunalStartDateStr={tribunalStartDate}
            coverageSet={selectedCoverage}
            tribunalName={selectedTribunal}
          />
        </div>

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
