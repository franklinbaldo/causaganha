/* Preact JSX transform handles h() automatically */

interface IconProps {
  className?: string;
}

const AlertCircleIcon = ({ className = "w-5 h-5" }: IconProps) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const ExternalLinkIcon = ({ className = "w-3 h-3" }: IconProps) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 3h6v6" />
    <path d="M10 14 21 3" />
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
  </svg>
);

interface Incident {
  streak: number;
  pr_url: string;
  pr_number: number | string;
  pr_blocked_by: string;
  latest_failing_run_url?: string;
}

interface IncidentBannerProps {
  incident: Incident | null | undefined;
}

export function IncidentBanner({ incident }: IncidentBannerProps) {
  if (!incident || incident.streak === 0) {
    return null;
  }

  return (
    <div
      className="card mb-6 border-l-4 border-l-danger bg-danger-muted/30 p-4"
      role="alert"
      aria-live="polite"
    >
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2 rounded-full bg-danger-muted shrink-0 mt-0.5 sm:mt-0">
            <AlertCircleIcon className="w-5 h-5 text-danger" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-danger mb-0.5">
              Critical Pipeline Failure
            </h3>
            <p className="text-xs sm:text-sm text-gray-700 dark:text-gray-300">
              Collect ZIPs on <code className="bg-white/50 dark:bg-black/20 px-1 py-0.5 rounded">main</code> has failed
              <span className="font-bold text-danger mx-1">{incident.streak} consecutive times</span>.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-2 w-full sm:w-auto mt-2 sm:mt-0 border-t sm:border-t-0 border-danger/10 pt-3 sm:pt-0">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500 font-medium">Fix Ready:</span>
            <a
              href={incident.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 font-medium text-accent hover:underline bg-accent-muted/30 px-2 py-0.5 rounded"
            >
              PR #{incident.pr_number} <ExternalLinkIcon />
            </a>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500 font-medium shrink-0">Blocked by:</span>
            <span className="inline-flex items-center bg-warning-muted/50 text-warning px-2 py-0.5 rounded font-medium whitespace-nowrap">
              {incident.pr_blocked_by}
            </span>
          </div>
          {incident.latest_failing_run_url && (
             <div className="flex items-center gap-2 text-[10px] mt-1">
               <a
                 href={incident.latest_failing_run_url}
                 target="_blank"
                 rel="noopener noreferrer"
                 className="text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 underline decoration-gray-300 dark:decoration-gray-600 underline-offset-2"
               >
                 View latest failing run
               </a>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}
