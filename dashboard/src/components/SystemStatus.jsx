import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';

// Inline SVG icons to avoid lucide-preact bundle overhead
const I = (d) => ({ className, ...r }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...r}>{d}</svg>
);

const ClockIcon = I([<circle cx="12" cy="12" r="10"/>, <polyline points="12 6 12 12 16 14"/>]);
const CheckCircleIcon = I([<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>, <polyline points="22 4 12 14.01 9 11.01"/>]);
const XCircleIcon = I([<circle cx="12" cy="12" r="10"/>, <line x1="15" y1="9" x2="9" y2="15"/>, <line x1="9" y1="9" x2="15" y2="15"/>]);
const ActivityIcon = I([<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>]);
const ChevronDownIcon = I([<path d="m6 9 6 6 6-6"/>]);
const ChevronUpIcon = I([<path d="m18 15-6-6-6 6"/>]);
const ExternalLinkIcon = I([<path d="M15 3h6v6"/>, <path d="M10 14 21 3"/>, <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>]);

const PIPELINE_INTERVAL_MINUTES = 20;

function useNextRunCountdown(lastRunTimestamp) {
  const [countdown, setCountdown] = useState('--:--');

  useEffect(() => {
    if (!lastRunTimestamp) return;

    const update = () => {
      const lastRun = new Date(lastRunTimestamp).getTime();
      const nextRun = lastRun + PIPELINE_INTERVAL_MINUTES * 60 * 1000;
      const remaining = Math.max(0, nextRun - Date.now());
      const mins = Math.floor(remaining / 60000);
      const secs = Math.floor((remaining % 60000) / 1000);
      setCountdown(`${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`);
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [lastRunTimestamp]);

  return countdown;
}

export function SystemStatus({ initialStats, initialCacheToday }) {
  const { data: allData } = useDataRefresh(null, null);
  const [showDetails, setShowDetails] = useState(false);

  // Use refreshed data if available, fall back to initial props
  const stats = allData?.stats ?? initialStats;
  const cacheToday = allData?.cacheData?.today ?? initialCacheToday;

  const countdown = useNextRunCountdown(stats?.timestamp);

  const isSuccess = stats?.status === 'success';
  const health = cacheToday?.health;
  const filesToday = cacheToday?.files_today;

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        {/* Left: status & stats */}
        <div className="flex items-center gap-8 flex-wrap">
          <div className="flex items-center gap-3" role="status" aria-live="polite">
            {stats ? (
              isSuccess ? (
                <div className="p-2 rounded-lg bg-success-muted">
                  <CheckCircleIcon className="w-4 h-4 text-success" aria-hidden="true" />
                </div>
              ) : (
                <div className="p-2 rounded-lg bg-danger-muted">
                  <XCircleIcon className="w-4 h-4 text-danger" aria-hidden="true" />
                </div>
              )
            ) : (
              <div className="w-8 h-8 rounded-lg bg-surface-overlay animate-pulse" />
            )}
            <div>
              <div className="text-sm font-medium text-content">
                {stats ? (isSuccess ? 'Pipeline Operational' : 'Pipeline Issue') : 'Loading...'}
              </div>
              {stats?.timestamp && (
                <div className="text-xs text-content-tertiary">
                  Last run: {new Date(stats.timestamp).toLocaleString()}
                </div>
              )}
              <span className="sr-only">
                {stats ? (isSuccess ? 'System operational' : 'System fault detected') : 'Loading system status'}
              </span>
            </div>
          </div>

          {/* Stat pills */}
          <div className="flex items-center gap-4 text-sm text-content-secondary">
            {health != null && (
              <div className="flex items-center gap-1.5">
                <ActivityIcon className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Health:</span>
                <span className={clsx("font-mono font-medium tabular-nums", health >= 70 ? "text-success" : "text-danger")}>
                  {health}%
                </span>
              </div>
            )}
            {filesToday != null && (
              <div className="flex items-center gap-1.5">
                <span>Today:</span>
                <span className="font-mono font-medium tabular-nums text-content">{filesToday}/91</span>
              </div>
            )}
            {stats?.duration_seconds != null && (
              <div className="hidden sm:flex items-center gap-1.5">
                <ClockIcon className="w-3.5 h-3.5" aria-hidden="true" />
                <span className="font-mono tabular-nums">{stats.duration_seconds}s</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: countdown & actions */}
        <div className="flex items-center gap-4">
          {stats?.timestamp && (
            <div className="hidden sm:block text-right">
              <div className="text-[10px] text-content-tertiary uppercase tracking-wider">Next run</div>
              <div className="text-lg font-mono font-semibold tabular-nums text-accent">{countdown}</div>
            </div>
          )}

          {stats?.steps && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="p-2 rounded-lg border border-border hover:bg-surface-overlay transition-colors"
              aria-expanded={showDetails}
              aria-label="Toggle run details"
            >
              {showDetails ? (
                <ChevronUpIcon className="w-4 h-4 text-content-secondary" aria-hidden="true" />
              ) : (
                <ChevronDownIcon className="w-4 h-4 text-content-secondary" aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expandable details */}
      {stats?.steps && (
        <div className={clsx(
          "transition-all duration-300 overflow-hidden",
          showDetails ? "max-h-[1000px] mt-5 opacity-100" : "max-h-0 opacity-0"
        )}>
          <div className="pt-4 border-t border-border">
            <h3 className="text-sm font-medium text-content mb-3">Pipeline Steps</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {Object.entries(stats.steps).map(([stepName, stepData]) => {
                const isOk = (stepData.success !== 0 && stepData.failed === 0) || stepData.success === true;

                return (
                  <div key={stepName} className="p-3 bg-surface rounded-lg border border-border-muted">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-content capitalize">
                        {stepName.replace(/_/g, ' ')}
                      </span>
                      <span className={clsx("badge gap-1", isOk ? "badge-success" : "badge-danger")}>
                        {isOk ? (
                          <CheckCircleIcon className="w-3 h-3" aria-hidden="true" />
                        ) : (
                          <XCircleIcon className="w-3 h-3" aria-hidden="true" />
                        )}
                        <span>{isOk ? 'OK' : 'Issue'}</span>
                      </span>
                    </div>
                    <div className="space-y-1 text-xs text-content-secondary">
                      {Object.entries(stepData).map(([k, v]) => {
                        if (k === 'success') return null;
                        return (
                          <div key={k} className="flex justify-between">
                            <span className="capitalize">{k.replace(/_/g, ' ')}</span>
                            <span className="font-mono tabular-nums text-content">{v}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-border-muted flex items-center justify-between text-xs text-content-tertiary">
        <span>Pipeline runs every {PIPELINE_INTERVAL_MINUTES} minutes via GitHub Actions</span>
        <a
          href="https://github.com/franklinbaldo/causaganha/actions"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 hover:text-accent transition-colors"
        >
          View Actions <ExternalLinkIcon className="w-3 h-3" aria-hidden="true" />
        </a>
      </div>
    </div>
  );
}
