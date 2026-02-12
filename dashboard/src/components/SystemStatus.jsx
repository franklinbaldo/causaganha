import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { Clock, CheckCircle, XCircle, Activity, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';
import { useDataRefresh } from '../lib/useDataRefresh';

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
                  <CheckCircle className="w-4 h-4 text-success" />
                </div>
              ) : (
                <div className="p-2 rounded-lg bg-danger-muted">
                  <XCircle className="w-4 h-4 text-danger" />
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
                <Activity className="w-3.5 h-3.5" />
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
                <Clock className="w-3.5 h-3.5" />
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
                <ChevronUp className="w-4 h-4 text-content-secondary" />
              ) : (
                <ChevronDown className="w-4 h-4 text-content-secondary" />
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
                      <span className={clsx("badge", isOk ? "badge-success" : "badge-danger")}>
                        {isOk ? 'OK' : 'Issue'}
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
          View Actions <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  );
}
