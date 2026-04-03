import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { useDataRefresh } from '../lib/useDataRefresh';

import type { ComponentChildren, JSX } from 'preact';

// Inline SVG icons to avoid lucide-preact bundle overhead
const createIcon = (d: ComponentChildren) =>
  ({ className, ...r }: JSX.SVGAttributes<SVGSVGElement>) => (
    <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...r}>{d}</svg>
  );

const ClockIcon = createIcon([<circle cx="12" cy="12" r="10"/>, <polyline points="12 6 12 12 16 14"/>]);
const CheckCircleIcon = createIcon([<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>, <polyline points="22 4 12 14.01 9 11.01"/>]);
const XCircleIcon = createIcon([<circle cx="12" cy="12" r="10"/>, <line x1="15" y1="9" x2="9" y2="15"/>, <line x1="9" y1="9" x2="15" y2="15"/>]);
const ActivityIcon = createIcon([<path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>]);
const ChevronDownIcon = createIcon([<path d="m6 9 6 6 6-6"/>]);
const ChevronUpIcon = createIcon([<path d="m18 15-6-6-6 6"/>]);
const ExternalLinkIcon = createIcon([<path d="M15 3h6v6"/>, <path d="M10 14 21 3"/>, <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>]);

const PIPELINE_INTERVAL_MINUTES = 20;

function useNextRunCountdown(lastRunTimestamp: string | null | undefined): string {
  const [countdown, setCountdown] = useState<string>('--:--');

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

interface SystemStatusProps {
  initialStats: any;
  initialCacheToday: any;
}

export function SystemStatus({ initialStats, initialCacheToday }: SystemStatusProps) {
  const { data: allData } = useDataRefresh(null, null);
  const [showDetails, setShowDetails] = useState<boolean>(false);

  // Use refreshed data if available, fall back to initial props
  const stats = allData?.stats ?? initialStats;
  const cacheToday = allData?.cacheData?.today ?? initialCacheToday;

  const countdown = useNextRunCountdown(stats?.timestamp);

  const isSuccess = stats?.status === 'success';
  const health = cacheToday?.health;
  const filesToday = cacheToday?.files_today;
  const dataDate = cacheToday?.date;
  const [now] = useState(() => Date.now());
  const isDataStale = (() => {
    if (!dataDate) return false;
    const today = new Date(now).toISOString().slice(0, 10);
    const yesterday = new Date(now - 86400000).toISOString().slice(0, 10);
    return dataDate !== today && dataDate !== yesterday;
  })();

  return (
    <article>
      <div>
        {/* Left: status & stats */}
        <div>
          <div role="status" aria-live="polite">
            {stats ? (
              isSuccess ? (
                <div className="bg-success-muted">
                  <CheckCircleIcon className="text-success" aria-hidden="true" />
                </div>
              ) : (
                <div className="bg-danger-muted">
                  <XCircleIcon className="text-danger" aria-hidden="true" />
                </div>
              )
            ) : (
              <div />
            )}
            <div>
              <div>
                {stats ? (isSuccess ? 'Pipeline Operational' : 'Pipeline Issue') : 'Loading...'}
              </div>
              {stats?.timestamp && (
                <small>
                  Last run: {new Date(stats.timestamp).toLocaleString()}
                </small>
              )}
              <span>
                {stats ? (isSuccess ? 'System operational' : 'System fault detected') : 'Loading system status'}
              </span>
            </div>
          </div>

          {/* Stat pills */}
          <div>
            {health != null && (
              <div>
                <ActivityIcon aria-hidden="true" />
                <span>Health:</span>
                <span className={clsx(health >= 70 ? "text-success" : "text-danger")}>
                  {health}%
                </span>
              </div>
            )}
            {filesToday != null && (
              <div>
                <span>{isDataStale ? dataDate : 'Today'}:</span>
                <span className={clsx(isDataStale && "text-warning")}>{filesToday}/91</span>
                {isDataStale && (
                  <span className="text-warning" title="Data collection appears stalled — no new data since this date">stale</span>
                )}
              </div>
            )}
            {stats?.duration_seconds != null && (
              <div>
                <ClockIcon aria-hidden="true" />
                <span>{stats.duration_seconds}s</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: countdown & actions */}
        <div>
          {stats?.timestamp && (
            <div>
              <small>Next run</small>
              <div className="text-accent">{countdown}</div>
            </div>
          )}

          {stats?.steps && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              aria-expanded={showDetails}
              aria-label="Toggle run details">
              {showDetails ? (
                <ChevronUpIcon aria-hidden="true" />
              ) : (
                <ChevronDownIcon aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expandable details */}
      {stats?.steps && showDetails && (
        <div>
          <div>
            <h3>Pipeline Steps</h3>
            <div>
              {Object.entries(stats.steps).map(([stepName, stepData]) => {
                const isOk = (stepData.success !== 0 && stepData.failed === 0) || stepData.success === true;

                return (
                  <div key={stepName}>
                    <div>
                      <span>
                        {stepName.replace(/_/g, ' ')}
                      </span>
                      <span className={clsx("badge", isOk ? "badge-success" : "badge-danger")}>
                        {isOk ? (
                          <CheckCircleIcon aria-hidden="true" />
                        ) : (
                          <XCircleIcon aria-hidden="true" />
                        )}
                        <span>{isOk ? 'OK' : 'Issue'}</span>
                      </span>
                    </div>
                    <div>
                      {Object.entries(stepData).map(([k, v]) => {
                        if (k === 'success') return null;
                        return (
                          <div key={k}>
                            <span>{k.replace(/_/g, ' ')}</span>
                            <span>{v}</span>
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

      {/* IA Task Status */}
      {cacheToday?.ia_tasks?.pending_count> 0 && (
        <div>
          <ClockIcon aria-hidden="true" />
          <span>{cacheToday.ia_tasks.pending_count} tarefa(s) de processamento pendente(s) no Internet Archive</span>
        </div>
      )}

      {/* Footer */}
      <footer>
        <small>Pipeline runs every {PIPELINE_INTERVAL_MINUTES} minutes via GitHub Actions</small>
        <a
          href="https://github.com/franklinbaldo/causaganha/actions" target="_blank"
          rel="noopener noreferrer">
          View Actions <ExternalLinkIcon aria-hidden="true" />
        </a>
      </footer>
    </article>
  );
}
