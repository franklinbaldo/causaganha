import { h } from 'preact';

export function IncidentBanner({ incident }) {
  if (!incident || !incident.active) {
    return null;
  }

  const {
    severity,
    collect_failure_streak,
    latest_failure_url,
    corrective_pr,
    remaining_blocker,
    causaganha_kilo_ready_count
  } = incident;

  const isCritical = severity === 'critical';
  const bgColor = isCritical ? 'bg-danger/10 border-danger/30' : 'bg-warning/10 border-warning/30';
  const textColor = isCritical ? 'text-danger' : 'text-warning';

  return (
    <div className={`mb-6 p-4 rounded-lg border ${bgColor} flex flex-col md:flex-row items-start md:items-center justify-between gap-4`} role="alert" aria-live="assertive">
      <div className="flex items-start gap-3">
        <div className={`mt-1 p-2 rounded-full ${isCritical ? 'bg-danger/20' : 'bg-warning/20'}`}>
          <svg className={`w-5 h-5 ${textColor}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <div>
          <h3 className={`font-semibold text-lg ${textColor}`}>
            Collect ZIPs Incident
          </h3>
          <div className="text-sm text-black dark:text-white mt-1 space-y-1">
            <p>
              <span className="font-medium">Streak:</span> {collect_failure_streak} consecutive failures.
              {latest_failure_url && (
                <a href={latest_failure_url} target="_blank" rel="noopener noreferrer" className="ml-1 text-accent hover:underline">
                  View Latest Run &rarr;
                </a>
              )}
            </p>
            {corrective_pr && (
              <p>
                <span className="font-medium">Fix PR:</span> <a href={corrective_pr.url} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">#{corrective_pr.number} {corrective_pr.title}</a>
              </p>
            )}
            <p>
              <span className="font-medium">Blocker:</span> {remaining_blocker}
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg p-3 text-center min-w-[120px] shadow-sm">
        <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold mb-1">Queue Health</div>
        <div className="text-2xl font-bold text-black dark:text-white" title="PRs that are ready except for Kilo Code Review">
          {causaganha_kilo_ready_count}
        </div>
        <div className="text-xs text-gray-400">Ready exc. Kilo</div>
      </div>
    </div>
  );
}
