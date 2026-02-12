import { SkeletonLoader, SkeletonText } from './SkeletonLoader';

export function YearProgress({ progressByYear }) {
  const progressData = progressByYear || {};
  const years = Object.entries(progressData).sort((a, b) => b[0] - a[0]);

  if (years.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center text-content-tertiary min-h-[200px]">
        <p className="text-sm">Year breakdown not available yet</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-content mb-5">Per-Year Breakdown</h2>
      <div className="space-y-5">
        {years.map(([year, data]) => {
          const pct = data.pct || 0;
          let barColor = 'bg-accent';
          let badgeClass = 'badge-accent';
          if (pct >= 90) {
            barColor = 'bg-success';
            badgeClass = 'badge-success';
          } else if (pct < 50) {
            barColor = 'bg-warning';
            badgeClass = 'badge-warning';
          }

          return (
            <div key={year}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-semibold font-mono text-content">{year}</span>
                  <span className={`badge ${badgeClass}`}>{pct.toFixed(1)}%</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-content-secondary">
                  <span>
                    <span className="font-mono tabular-nums font-medium text-content">{data.unique_days}</span> collected
                  </span>
                  {data.days_consolidated > 0 && (
                    <span>
                      <span className="font-mono tabular-nums font-medium text-purple">{data.days_consolidated}</span> consolidated
                    </span>
                  )}
                </div>
              </div>
              <div className="w-full h-2.5 bg-surface-overlay rounded-full overflow-hidden">
                <div
                  className={`h-full ${barColor} rounded-full transition-all duration-700`}
                  style={{ width: `${Math.min(pct, 100)}%` }}
                  role="progressbar"
                  aria-valuenow={pct}
                  aria-valuemin="0"
                  aria-valuemax="100"
                  aria-label={`${year}: ${pct.toFixed(1)}% complete`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
