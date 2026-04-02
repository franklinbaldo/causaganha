import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';
import { TRIBUNAIS } from '../lib/tribunais.js';

export function TribunalView({ initialCoverage, initialEtas, initialTargetRange, initialStartDates, initialQualityScores, initialPipeline, initialProgressByYear, initialVolume, initialVelocityMetrics, initialIaSnapshot }) {
  const { data: allData } = useDataRefresh(null, null);

  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const startDates = allData?.tribunalStartDates ?? initialStartDates;
  const qualityScores = allData?.tribunalQualityScores ?? initialQualityScores ?? {};
  const pipeline = allData?.cacheData?.today?.pipeline ?? initialPipeline;
  const progressByYear = allData?.progressByYear ?? initialProgressByYear;
  const volume = allData?.volume ?? initialVolume;
  const velocity = allData?.velocityMetrics ?? initialVelocityMetrics;
  const iaSnapshot = allData?.iaSnapshot ?? initialIaSnapshot;

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
      velocity={velocity}
      iaSnapshot={iaSnapshot}
    />
  );
}

function formatEtaText(etaDays) {
  if (etaDays === null || etaDays === undefined) return 'Pipeline parado';
  if (etaDays < 30) return `~${etaDays} dias`;
  if (etaDays < 365) return `~${Math.round(etaDays / 30)} meses`;
  const years = (etaDays / 365).toFixed(1);
  return `~${years} anos`;
}

function OverviewGrid({ tribunals, coverage, etas, startDates, qualityScores, pipeline, progressByYear, volume, velocity, iaSnapshot }) {
  // Prefer IA snapshot data (fresh, direct from IA) over pipeline/backfill data
  const snap = iaSnapshot?.summary;
  const totalZips = snap?.total_zips || pipeline?.total_zips || 0;
  const totalGB = snap?.total_size_gb || volume?.total_gb || 0;
  const tribunalsWithData = snap?.tribunals_with_data || 0;
  const latestDate = snap?.latest_collection_date;
  const daysConsolidated = pipeline?.days_consolidated || 0;
  const snapshotAge = iaSnapshot?.generated_at;

  // Per-tribunal zip counts from snapshot
  const snapshotItems = iaSnapshot?.items || {};
  const snapshotByYear = iaSnapshot?.by_year || {};

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
              {totalZips.toLocaleString()} ZIPs no Internet Archive
            </p>
            {latestDate && (
              <p className="text-gray-500 text-xs font-mono mt-1">
                Ultima coleta: {latestDate}
                {snapshotAge && <span className="ml-2 text-gray-600">| Snapshot: {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>}
              </p>
            )}
          </div>

          <div className="text-right flex flex-col items-end">
            <span className="text-4xl font-black text-accent font-mono leading-none">{tribunalsWithData}</span>
            <span className="text-[10px] text-gray-500 uppercase font-bold mt-1">Tribunais com dados</span>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-4 border-t border-slate-800">
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">ZIPs no IA</span>
              <span className="text-lg font-bold font-mono text-accent">
                {totalZips.toLocaleString()}
              </span>
           </div>
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Volume</span>
              <span className="text-lg font-bold font-mono text-info">
                {totalGB.toFixed(1)} GB
              </span>
           </div>
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Tribunais</span>
              <span className="text-lg font-bold font-mono text-success">
                {tribunalsWithData} / {snap?.tribunals_total || 96}
              </span>
           </div>
           <div className="flex flex-col">
              <span className="text-[9px] text-gray-500 uppercase font-bold tracking-tighter">Items no IA</span>
              <span className="text-lg font-bold font-mono text-warning">
                {snap?.total_items || 0}
              </span>
           </div>
        </div>

      </div>

      {/* Progress by Year — prefer snapshot data */}
      {Object.keys(snapshotByYear).length > 0 ? (
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-black dark:text-white mb-4">ZIPs por Ano (Internet Archive)</h3>
          <div className="space-y-4">
            {Object.entries(snapshotByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                return (
                  <div key={year}>
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="font-mono font-bold text-black dark:text-white">{year}</span>
                      <span className="font-mono font-bold text-sm text-accent">{d.zip_count.toLocaleString()} zips</span>
                    </div>
                    <div className="flex gap-4 mt-1 text-[10px] text-gray-500 dark:text-gray-400 font-mono">
                      <span>{d.tribunals_with_data} / {d.tribunals_total} tribunais</span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      ) : progressByYear && Object.keys(progressByYear).length > 0 ? (
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
      ) : null}

      {/* Tribunals Grid — data from IA snapshot */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {tribunals.map(t => {
          // Aggregate snapshot data for this tribunal across all years
          let totalZips = 0;
          let latestDate = null;
          let earliestDate = null;
          if (snapshotItems) {
            for (const item of Object.values(snapshotItems)) {
              if (item.tribunal === t) {
                totalZips += item.zip_count;
                if (!latestDate || item.latest_date > latestDate) latestDate = item.latest_date;
                if (!earliestDate || item.earliest_date < earliestDate) earliestDate = item.earliest_date;
              }
            }
          }
          const hasData = totalZips > 0;

          return (
            <a
              key={t}
              href={`${baseUrl}monitor/${t.toLowerCase()}`}
              className="group card p-4 flex flex-col gap-3 cursor-pointer hover:border-accent transition-all duration-200 hover:shadow-lg relative overflow-hidden no-underline"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-gray-900 dark:text-white group-hover:text-accent transition-colors">{t}</h3>
                <span className={clsx(
                  "text-xs font-bold font-mono",
                  hasData ? "text-accent" : "text-gray-400 dark:text-gray-600"
                )}>
                  {totalZips > 0 ? totalZips.toLocaleString() : '—'}
                </span>
              </div>

              {hasData ? (
                <>
                  <div className="text-[10px] text-gray-500 dark:text-gray-400 font-mono">
                    {earliestDate} a {latestDate}
                  </div>
                  <div className="h-1.5 w-full bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent rounded-full transition-all duration-700"
                      style={{ width: `${Math.min(100, (totalZips / (snap?.total_zips || totalZips)) * 300)}%` }}
                    />
                  </div>
                </>
              ) : (
                <div className="text-[10px] text-gray-400 dark:text-gray-600">
                  Sem dados no IA
                </div>
              )}
            </a>
          );
        })}
      </div>
    </div>
  );
}
