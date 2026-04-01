import { useState } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';
import { TRIBUNAIS } from '../lib/tribunais.js';

export function TribunalView({ initialCoverage, initialEtas, initialTargetRange, initialStartDates, initialQualityScores, initialPipeline, initialProgressByYear, initialVolume }) {
  const { data: allData } = useDataRefresh(null, null);

  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const startDates = allData?.tribunalStartDates ?? initialStartDates;
  const qualityScores = allData?.tribunalQualityScores ?? initialQualityScores ?? {};
  const pipeline = allData?.cacheData?.today?.pipeline ?? initialPipeline;
  const progressByYear = allData?.progressByYear ?? initialProgressByYear;
  const volume = allData?.volume ?? initialVolume;

  return (
    <OverviewGrid
      tribunals={TRIBUNAIS}
      coverage={coverage}
      etas={etas}
      startDates={startDates}
      qualityScores={qualityScores}
      pipeline={pipeline}
      progressByYear={progressByYear}
      volume={volume}
    />
  );
}

function OverviewGrid({ tribunals, coverage, etas, startDates, qualityScores, pipeline, progressByYear, volume }) {
  const backfillDone = pipeline?.backfill_done || 0;
  const backfillTotal = pipeline?.backfill_total || 1;
  const totalZips = pipeline?.total_zips || 0;
  const daysConsolidated = pipeline?.days_consolidated || 0;
  const progressPct = pipeline?.progress_pct || 0;

  const activeTribunals = Object.values(etas).filter(e => e.velocity_14d > 0).length;
  const totalTracked = Object.keys(etas).length;
  const totalGB = volume?.total_gb || 0;

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

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

      {/* Tribunals Grid — cards link to /monitor/{tribunal} */}
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
            <a
              key={t}
              href={`${baseUrl}monitor/${t.toLowerCase()}`}
              className="group card p-4 flex flex-col gap-3 cursor-pointer hover:border-accent transition-all duration-200 hover:shadow-lg relative overflow-hidden no-underline"
            >
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
                    style={{ width: `${Math.min(100, completionPct)}%` }}
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
            </a>
          );
        })}
      </div>
    </div>
  );
}
