import { useState } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';
import { TRIBUNAIS } from '../lib/tribunais.js';
import { Heatmap, VelocityTimeline, calculateVelocityAndRegression } from './Heatmap';

export function TribunalDetail({ tribunalCode, initialCoverage, initialEtas, initialTargetRange, initialStartDates, initialQualityScores }) {
  const { data: allData } = useDataRefresh(null, null);
  const [selectedTribunal, setSelectedTribunal] = useState(tribunalCode.toUpperCase());

  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const absentCoverage = allData?.tribunalAbsentCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const startDates = allData?.tribunalStartDates ?? initialStartDates ?? {};
  const qualityScores = allData?.tribunalQualityScores ?? initialQualityScores ?? {};
  const iaSnapshot = allData?.iaSnapshot;

  // Derive targetRange dynamically — no hardcoded dates
  const backfillTargetRange = allData?.targetRange ?? initialTargetRange;
  const today = new Date().toISOString().split('T')[0];
  const targetRange = {
    start: backfillTargetRange?.start || "2024-01-01",
    end: backfillTargetRange?.end || today,
  };

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  const handleTribunalChange = (e) => {
    const newTribunal = e.target.value;
    setSelectedTribunal(newTribunal);
    window.location.href = `${baseUrl}monitor/${newTribunal.toLowerCase()}`;
  };

  // Build coverage from IA snapshot (real ZIPs on IA) — prefer over backfill data
  const snapshotDates = new Set();
  if (iaSnapshot?.items) {
    for (const item of Object.values(iaSnapshot.items)) {
      if (item.tribunal === selectedTribunal) {
        item.dates.forEach(d => snapshotDates.add(d));
      }
    }
  }
  const selectedCoverage = snapshotDates.size > 0 ? snapshotDates : new Set(coverage[selectedTribunal] || []);
  const selectedEtaData = etas[selectedTribunal] || { missing_days: null, velocity_14d: 0, eta_days: null };
  const tribunalStartDate = startDates[selectedTribunal] || selectedEtaData.genesis_date;

  // Calculate expected days from tribunal start to target end
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
    etaText = "Complete";
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

  const totalForBar = actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between mb-2">
        <a
          href={`${baseUrl}monitor`}
          className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors"
        >
          <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Voltar
        </a>
      </div>

      <div className="card p-4 flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <div className="w-full lg:w-64 flex flex-col gap-4 flex-shrink-0">
          <div>
            <label htmlFor="tribunal-select" className="block text-sm font-medium text-black dark:text-white mb-2">
              Tribunal
            </label>
            <select
              id="tribunal-select"
              value={selectedTribunal}
              onChange={handleTribunalChange}
              className="w-full bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-black dark:text-white focus:outline-none focus:border-accent"
            >
              {TRIBUNAIS.map(t => (
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
                  style={{ width: totalForBar > 0 ? `${(selectedCoverage.size / totalForBar) * 100}%` : '0%' }}
                  title={`Sincronizado: ${selectedCoverage.size} ZIPs`}
                />
                <div
                  className="h-full bg-warning opacity-70 transition-all duration-700 ease-out"
                  style={{ width: totalForBar > 0 ? `${((selectedEtaData.absent_days_count || 0) / totalForBar) * 100}%` : '0%' }}
                  title={`Vazio Confirmado: ${selectedEtaData.absent_days_count || 0} dias`}
                />
              </div>
              <div className="flex justify-between mt-2 text-[9px] font-bold uppercase tracking-tighter">
                <div className="flex items-center gap-1.5 grayscale opacity-70">
                  <div className="w-2 h-2 rounded-full bg-accent"></div>
                  <span>{totalForBar > 0 ? ((selectedCoverage.size / totalForBar) * 100).toFixed(1) : '0.0'}% Sync</span>
                </div>
                <div className="flex items-center gap-1.5 text-right grayscale opacity-70">
                  <span>{totalForBar > 0 ? (((selectedEtaData.absent_days_count || 0) / totalForBar) * 100).toFixed(1) : '0.0'}% Absent</span>
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
            baseUrl={baseUrl}
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
