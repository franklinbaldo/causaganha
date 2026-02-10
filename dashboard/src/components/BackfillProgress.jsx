import clsx from 'clsx';

export function BackfillProgress({ stats }) {
  // Fallback if detailed backfill data is missing
  const progressData = stats?.backfill?.progress_by_year || {
    "2026": { completed: 0, total: 365, pct: 0 },
    "2025": { completed: 0, total: 365, pct: 0 },
    "2024": { completed: 0, total: 366, pct: 0 },
    "2023": { completed: 0, total: 365, pct: 0 },
    "2022": { completed: 0, total: 365, pct: 0 },
    "2021": { completed: 0, total: 365, pct: 0 },
  };

  // If we have global progress but no details, maybe distribute it?
  // Or just show what we have.

  const years = Object.entries(progressData).sort((a, b) => b[0] - a[0]);

  return (
    <div className="cyber-card h-full">
      <h2 className="text-lg font-bold text-cyber-primary mb-4 flex justify-between items-center">
        <span>Backfill Progress</span>
        {stats?.steps?.catalog?.backfill_progress_pct !== undefined && (
             <span className="text-sm text-cyber-secondary">
               Total: {stats.steps.catalog.backfill_progress_pct}%
             </span>
        )}
      </h2>

      <div className="space-y-3">
        {years.map(([year, data]) => (
          <div key={year} className="group">
            <div className="flex justify-between text-sm mb-1.5 font-bold">
              <span className="font-mono text-cyber-text group-hover:text-cyber-primary transition-colors">{year}</span>
              <span className="text-cyber-muted">{data.completed}/{data.total} ({data.pct}%)</span>
            </div>
            <div className="h-5 bg-cyber-dark border border-cyber-border rounded-sm overflow-hidden relative">
               <div className="absolute inset-0 opacity-20 bg-[linear-gradient(90deg,transparent_50%,#333_50%)] bg-[length:4px_100%]" />

               <div
                 className="h-full bg-cyber-secondary relative shadow-[0_0_5px_rgba(0,255,65,0.5)]"
                 style={{ width: `${data.pct}%` }}
               >
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
