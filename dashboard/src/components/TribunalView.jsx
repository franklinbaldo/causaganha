import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';
import { CellTooltip } from './CellTooltip';

function calculateVelocityAndRegression(coverageSet, targetRangeEndStr, tribunalStartDateStr) {
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

  let trend = 0;
  if (historicalAvgVelocity > 0) {
    trend = ((currentVelocity - historicalAvgVelocity) / historicalAvgVelocity) * 100;
  } else if (currentVelocity > 0) {
    trend = 100;
  }

  let baselineCoverage = 0;
  if (baseline60Days > 0) baselineCoverage = baseline60Collected / baseline60Days;

  let currentCoverage = 0;
  if (current30Days > 0) currentCoverage = current30Collected / current30Days;

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

const TRIBUNALS = [
  "STF", "STJ", "TST", "TSE", "STM", "CNJ",
  "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
  "TRT1", "TRT2", "TRT3", "TRT4", "TRT5", "TRT6", "TRT7", "TRT8", "TRT9", "TRT10", "TRT11", "TRT12", "TRT13", "TRT14", "TRT15", "TRT16", "TRT17", "TRT18", "TRT19", "TRT20", "TRT21", "TRT22", "TRT23", "TRT24",
  "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT", "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA", "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO", "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJTO",
  "TRE-AC", "TRE-AL", "TRE-AM", "TRE-AP", "TRE-BA", "TRE-CE", "TRE-DF", "TRE-ES", "TRE-GO", "TRE-MA", "TRE-MG", "TRE-MS", "TRE-MT", "TRE-PA", "TRE-PB", "TRE-PE", "TRE-PI", "TRE-PR", "TRE-RJ", "TRE-RN", "TRE-RO", "TRE-RR", "TRE-RS", "TRE-SC", "TRE-SE", "TRE-SP", "TRE-TO"
];

export function TribunalView({ initialCoverage, initialEtas, initialTargetRange, initialStartDates, initialQualityScores, initialPipeline, initialProgressByYear, initialVolume, initialTribunalStats }) {
  const { data: allData } = useDataRefresh(null, null);
  const [viewMode, setViewMode] = useState("overview"); // "overview" | "detail"
  const [selectedTribunal, setSelectedTribunal] = useState("STF");

  // Prefer fresh client-side data, fall back to build-time props
  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const absentCoverage = allData?.tribunalAbsentCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const targetRange = allData?.targetRange ?? initialTargetRange ?? { start: "2024-01-01", end: "2026-02-03" };
  const startDates = allData?.tribunalStartDates ?? initialStartDates;
  const qualityScores = allData?.tribunalQualityScores ?? initialQualityScores ?? {};
  const pipeline = allData?.cacheData?.today?.pipeline ?? initialPipeline;
  const progressByYear = allData?.progressByYear ?? initialProgressByYear;
  const volume = allData?.volume ?? initialVolume;

  const handleSelectTribunal = (t) => {
    setSelectedTribunal(t);
    setViewMode("detail");
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (viewMode === "overview") {
    return (
      <OverviewGrid
        tribunals={TRIBUNALS}
        coverage={coverage}
        absentCoverage={absentCoverage}
        etas={etas}
        startDates={startDates}
        qualityScores={qualityScores}
        onSelect={handleSelectTribunal}
        pipeline={pipeline}
        progressByYear={progressByYear}
        volume={volume}
      />
    );
  }

  // Detail View Logic
  const selectedCoverage = new Set(coverage[selectedTribunal] || []);
  const selectedEtaData = etas[selectedTribunal] || { missing_days: null, velocity_14d: 0, eta_days: null };
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

  const actualMissingDays = selectedEtaData.missing_days !== null
    ? selectedEtaData.missing_days
    : Math.max(0, expectedDays - selectedCoverage.size);

  const isStopped = selectedEtaData.stopped || false;
  const cursorDate = selectedEtaData.cursor_date;
  const completionPct = selectedEtaData.completion_pct || 0;
  const genesisDate = selectedEtaData.genesis_date || tribunalStartDate;

  const velocityMetrics = calculateVelocityAndRegression(selectedCoverage, targetRange.end, tribunalStartDate);

  let dynamicEtaDays = selectedEtaData.eta_days;
  if (velocityMetrics && velocityMetrics.currentVelocity > 0 && actualMissingDays > 0) {
    dynamicEtaDays = Math.ceil(actualMissingDays / (velocityMetrics.currentVelocity / 7));
  }

  let etaText = "Pending";
  if (actualMissingDays === 0 && expectedDays > 0) {
    etaText = "Complete ✓";
  } else if (dynamicEtaDays) {
    if (dynamicEtaDays < 30) {
      etaText = `~${dynamicEtaDays} days`;
    } else {
      const months = Math.round(dynamicEtaDays / 30);
      etaText = `~${months} month${months > 1 ? 's' : ''}`;
    }
  }

  const isComplete = actualMissingDays === 0 && expectedDays > 0;
  const statusColor = isComplete ? "text-success" : "text-warning";

  const absentList = absentCoverage[selectedTribunal] || [];
  const absentSet = new Set(absentList);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between mb-2">
        <button 
          onClick={() => setViewMode("overview")}
          className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors"
        >
          <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Overview
        </button>
      </div>

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

          <div className="flex flex-col gap-2 p-3 bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-100 dark:border-slate-800 relative">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-black dark:text-white">{selectedTribunal}</h3>
              {qualityScores[selectedTribunal] && (
                <div
                  className={clsx(
                    "text-[10px] font-bold px-1.5 py-0.5 rounded cursor-help",
                    qualityScores[selectedTribunal].grade === 'A' ? "bg-success text-white" :
                    qualityScores[selectedTribunal].grade === 'B' ? "bg-info text-white" :
                    qualityScores[selectedTribunal].grade === 'C' ? "bg-warning text-white" :
                    qualityScores[selectedTribunal].grade === 'D' ? "bg-danger text-white" :
                    "bg-gray-500 text-white"
                  )}
                  title={`Completeness: ${qualityScores[selectedTribunal].completeness}%\nRecency: ${qualityScores[selectedTribunal].recency}%\nConsistency: ${qualityScores[selectedTribunal].consistency}%`}
                >
                  Grade {qualityScores[selectedTribunal].grade}
                </div>
              )}
            </div>

            <div className="text-sm flex justify-between mt-2">
              <span className="text-gray-600 dark:text-gray-300">Genesis</span>
              <span className="font-mono text-black dark:text-white">{genesisDate || "Unknown"}</span>
            </div>

            <div className="mt-2 mb-4">
              <div className="flex justify-between text-[11px] mb-1.5">
                <span className="text-gray-500 uppercase tracking-wider font-bold">Archiving Progress</span>
                <span className="font-mono font-bold text-accent">{completionPct}%</span>
              </div>
              <div className="h-3 w-full bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden flex shadow-inner">
                <div
                  className="h-full bg-gradient-to-r from-accent to-accent-light transition-all duration-700 ease-out"
                  style={{ width: `${(selectedCoverage.size / (actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0))) * 100}%` }}
                  title={`Sincronizado: ${selectedCoverage.size} ZIPs`}
                />
                <div
                  className="h-full bg-warning opacity-70 transition-all duration-700 ease-out"
                  style={{ width: `${((selectedEtaData.absent_days_count || 0) / (actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0))) * 100}%` }}
                  title={`Vazio Confirmado: ${selectedEtaData.absent_days_count || 0} dias`}
                />
              </div>
              <div className="flex justify-between mt-2 text-[9px] font-bold uppercase tracking-tighter">
                <div className="flex items-center gap-1.5 grayscale opacity-70">
                  <div className="w-2 h-2 rounded-full bg-accent"></div>
                  <span>{( (selectedCoverage.size / (actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0))) * 100).toFixed(1)}% Sync</span>
                </div>
                <div className="flex items-center gap-1.5 text-right grayscale opacity-70">
                  <span>{( ((selectedEtaData.absent_days_count || 0) / (actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0))) * 100).toFixed(1)}% Absent</span>
                  <div className="w-2 h-2 rounded-full bg-warning"></div>
                </div>
              </div>
            </div>

            <div className="text-sm flex justify-between">
              <span className="text-gray-600 dark:text-gray-300">Status</span>
              <span className={`font-medium ${statusColor}`}>{etaText}</span>
            </div>

            <div className="text-sm flex justify-between">
              <span className="text-gray-600 dark:text-gray-300">Missing</span>
              <span className="font-mono text-black dark:text-white">{actualMissingDays} days</span>
            </div>

            {cursorDate && !isStopped && (
              <div className="text-sm flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">Scanning cursor</span>
                <span className="font-mono text-xs font-semibold text-accent animate-pulse">{cursorDate}</span>
              </div>
            )}

            {isStopped && (
              <div className="mt-1">
                <span className="badge badge-danger text-[10px] w-full justify-center">
                  Stopped (60d Empty Streak)
                </span>
              </div>
            )}
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
            velocityMetrics={{ 
              ...velocityMetrics, 
              absentSet: absentSet 
            }}
          />
        </div>
      </div>
    </div>
  );
}

function OverviewGrid({ tribunals, coverage, etas, startDates, absentCoverage, qualityScores, onSelect, pipeline, progressByYear, volume }) {
  // Use pipeline data from backfill.json (source of truth) instead of manual calculation
  const backfillDone = pipeline?.backfill_done || 0;
  const backfillTotal = pipeline?.backfill_total || 1;
  const totalZips = pipeline?.total_zips || 0;
  const daysConsolidated = pipeline?.days_consolidated || 0;
  const progressPct = pipeline?.progress_pct || 0;

  const activeTribunals = Object.values(etas).filter(e => e.velocity_14d > 0).length;
  const totalTracked = Object.keys(etas).length;
  const totalGB = volume?.total_gb || 0;

  return (
    <div className="flex flex-col gap-6 pb-8">
      {/* Global Progress Banner */}
      <div className="card p-6 bg-slate-900 border-slate-800 text-white relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-accent/10 to-transparent opacity-50 animate-pulse-slow"></div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-bold tracking-tight">Progresso do Arquivo</h2>
            <p className="text-gray-400 text-sm font-medium uppercase tracking-widest font-mono">
              {backfillDone.toLocaleString()} / {backfillTotal.toLocaleString()} itens coletados
            </p>
          </div>

          <div className="text-right flex flex-col items-end">
            <span className="text-4xl font-black text-accent font-mono leading-none">{progressPct.toFixed(1)}%</span>
            <span className="text-[10px] text-gray-500 uppercase font-bold mt-1">Progresso Global</span>
          </div>
        </div>

        <div className="relative mt-6">
          <div className="h-4 w-full bg-slate-800 rounded-full overflow-hidden p-1 shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-accent to-accent-light rounded-sm transition-all duration-1000 ease-out shadow-[0_0_15px_rgba(59,130,246,0.3)]"
              style={{ width: `${Math.min(100, progressPct)}%` }}
              title={`${backfillDone.toLocaleString()} itens coletados`}
            />
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-4 border-t border-slate-800">
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">ZIPs Coletados</span>
              <span className="text-lg font-bold font-mono text-accent">
                {totalZips.toLocaleString()}
              </span>
           </div>
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Volume Total</span>
              <span className="text-lg font-bold font-mono text-info">
                {totalGB.toFixed(1)} GB
              </span>
           </div>
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Tribunais Ativos</span>
              <span className="text-lg font-bold font-mono text-success">
                {activeTribunals} / {totalTracked}
              </span>
           </div>
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Dias Consolidados</span>
              <span className="text-lg font-bold font-mono text-warning">
                {daysConsolidated}
              </span>
           </div>
        </div>
      </div>

      {/* Progress by Year */}
      {progressByYear && Object.keys(progressByYear).length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-black dark:text-white mb-4">Progresso por Ano</h3>
          <div className="space-y-4">
            {Object.entries(progressByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                const pct = d.pct || 0;
                return (
                  <div key={year}>
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="font-mono font-bold text-black dark:text-white">{year}</span>
                      <span className={`font-mono font-bold text-sm ${
                        pct >= 80 ? 'text-green-600 dark:text-green-400' :
                        pct >= 30 ? 'text-yellow-600 dark:text-yellow-400' :
                        'text-gray-500 dark:text-gray-400'
                      }`}>{pct.toFixed(1)}%</span>
                    </div>
                    <div className="h-3 w-full bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          pct >= 80 ? 'bg-green-500' :
                          pct >= 30 ? 'bg-yellow-500' :
                          pct > 0 ? 'bg-red-500' :
                          'bg-gray-300 dark:bg-gray-600'
                        }`}
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                    <div className="flex gap-4 mt-1 text-[10px] text-gray-500 dark:text-gray-400 font-mono">
                      <span>{d.zips || 0} zips</span>
                      <span>{d.days_consolidated || 0} consolidados</span>
                      <span>{d.unique_days || 0} / {d.weekdays || 0} dias</span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Tribunals Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {tribunals.map(t => {
          const etaData = etas[t] || {};
          const completionPct = etaData.completion_pct || 0;
          const isStopped = etaData.stopped || false;
          const cursorDate = etaData.cursor_date;
          const missingDays = etaData.missing_days || 0;
          const isComplete = missingDays === 0 && completionPct === 100;
          const grade = qualityScores[t]?.grade;

          return (
            <div 
              key={t}
              onClick={() => onSelect(t)}
              className="group card p-4 flex flex-col gap-3 cursor-pointer hover:border-accent transition-all duration-200 hover:shadow-lg relative overflow-hidden"
            >
              {/* Background pulsing effect for scanning tribunals */}
              {cursorDate && !isStopped && (
                <div className="absolute top-0 right-0 p-2">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
                  </span>
                </div>
              )}

              <div className="flex items-center justify-between">
                <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-accent transition-colors">{t}</h3>
                {grade && (
                  <span className={clsx(
                    "text-[9px] font-bold px-1.5 py-0.5 rounded",
                    grade === 'A' ? "bg-success/20 text-success" :
                    grade === 'B' ? "bg-info/20 text-info" :
                    grade === 'C' ? "bg-warning/20 text-warning" :
                    "bg-danger/20 text-danger"
                  )}>
                    Grade {grade}
                  </span>
                )}
              </div>

              <div className="flex-1">
                <div className="flex justify-between text-[11px] mb-1.5">
                  <span className="text-gray-500 dark:text-gray-400 font-medium">Archiving Progress</span>
                  <span className="font-mono font-bold text-black dark:text-white">{completionPct.toFixed(0)}%</span>
                </div>
                <div className="h-2 w-full bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
                  <div
                    className={clsx(
                      "h-full transition-all duration-1000 ease-out",
                      isComplete ? "bg-success" : "bg-accent"
                    )}
                    style={{ width: `${(coverage[t]?.length / (etaData.missing_days + coverage[t]?.length + (etaData.absent_days_count || 0))) * 100}%` }}
                  />
                  <div
                    className="h-full bg-warning opacity-60 transition-all duration-1000 ease-out"
                    style={{ width: `${((etaData.absent_days_count || 0) / (etaData.missing_days + coverage[t]?.length + (etaData.absent_days_count || 0))) * 100}%` }}
                  />
                </div>
              </div>

              <div className="flex justify-between items-center text-[10px] font-mono">
                <div className="flex flex-col">
                  <span className="text-gray-400 uppercase text-[8px] leading-3 tracking-tighter">Status</span>
                  <span className={clsx(
                    "font-bold",
                    isComplete ? "text-success" :
                    isStopped ? "text-danger" :
                    cursorDate ? "text-accent" : "text-gray-500"
                  )}>
                    {isComplete ? "COMPLETE" : isStopped ? "STOPPED" : cursorDate ? "SCANNING" : "PENDING"}
                  </span>
                </div>
                <div className="flex flex-col text-right">
                  <span className="text-gray-400 uppercase text-[8px] leading-3 tracking-tighter">Missing</span>
                  <span className="text-gray-600 dark:text-gray-300 font-bold">{missingDays}d</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function VelocityTimeline({ metrics }) {
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

function Heatmap({ globalStartDateStr, globalEndDateStr, tribunalStartDateStr, coverageSet, tribunalName, velocityMetrics }) {
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
    // Check if the date is in the absent set (passed via props or derived)
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
    if (status === 'absent') return `${dateStr}: Confirmed Absent (No journal publisher)`;
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
    if (type === 'click' && hoveredCell?.data?.date === dateStr) {
      setHoveredCell(null);
      return;
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
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar { height: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: 4px; }
        .custom-scrollbar:hover::-webkit-scrollbar-thumb { background: var(--color-content-tertiary); }
      `}</style>
    </div>
  );
}
