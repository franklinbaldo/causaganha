import clsx from 'clsx';

export function BackfillProgress({ progressByYear, totalPct }) {
  const progressData = progressByYear || {};
  const years = Object.entries(progressData).sort((a, b) => b[0] - a[0]);

  if (years.length === 0) {
    return (
      <div className="cyber-card h-full flex flex-col items-center justify-center text-cyber-muted min-h-[200px]">
        <p className="text-sm">Backfill data not available yet</p>
      </div>
    );
  }

  return (
    <div className="cyber-card h-full">
      <h2 className="text-lg font-bold text-cyber-primary mb-4 flex justify-between items-center">
        <span>Backfill Progress</span>
        {totalPct !== undefined && (
             <span className="text-sm text-cyber-secondary">
               Total: {totalPct}%
             </span>
        )}
      </h2>

      <div className="space-y-3">
        {years.map(([year, data]) => (
          <div key={year} className="group">
            <div className="flex justify-between text-sm mb-1.5 font-bold">
              <span className="font-mono text-cyber-text group-hover:text-cyber-primary transition-colors">{year}</span>
              <span className="text-cyber-muted">
                {data.unique_days}d collected
                {data.days_consolidated > 0 && (
                  <span className="text-cyber-secondary ml-2">
                    {data.days_consolidated}d consolidated
                  </span>
                )}
                <span className="ml-2">({data.pct}%)</span>
              </span>
            </div>
            <div className="h-5 bg-cyber-dark border border-cyber-border rounded-sm overflow-hidden relative">
               <div className="absolute inset-0 opacity-20 bg-[linear-gradient(90deg,transparent_50%,#333_50%)] bg-[length:4px_100%]" />

               <div
                 className={clsx(
                   "h-full relative",
                   data.pct >= 90 ? "bg-cyber-primary shadow-[0_0_5px_rgba(0,255,65,0.5)]" :
                   data.pct >= 50 ? "bg-cyber-secondary shadow-[0_0_5px_rgba(0,255,65,0.3)]" :
                   "bg-cyber-warning shadow-[0_0_5px_rgba(255,200,0,0.3)]"
                 )}
                 style={{ width: `${Math.min(data.pct, 100)}%` }}
               >
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
