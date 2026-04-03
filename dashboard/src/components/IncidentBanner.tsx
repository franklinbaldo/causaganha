/* Preact JSX transform handles h() automatically */

interface IconProps {
  className?: string;
}

const AlertCircleIcon = ({ className }: IconProps) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);

const ExternalLinkIcon = ({ className }: IconProps) => (
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
    <article
      className="border-l-danger bg-danger-muted" role="alert"
      aria-live="polite">
      <header>
        <AlertCircleIcon className="text-danger" />
        <hgroup>
          <h3 className="text-danger">
            Critical Pipeline Failure
          </h3>
          <p>
            Collect ZIPs on <code>main</code> has failed
            <span className="text-danger"> {incident.streak} consecutive times</span>.
          </p>
        </hgroup>
      </header>

      <div>
        <div>
          <span>Fix Ready:</span>
          <a
            href={incident.pr_url} target="_blank"
            rel="noopener noreferrer"
            className="text-accent bg-accent-muted">
            PR #{incident.pr_number} <ExternalLinkIcon />
          </a>
        </div>
        <div>
          <span>Blocked by:</span>
          <span className="bg-warning-muted text-warning">
            {incident.pr_blocked_by}
          </span>
        </div>
        {incident.latest_failing_run_url && (
           <div>
             <a
               href={incident.latest_failing_run_url} target="_blank"
               rel="noopener noreferrer">
               View latest failing run
             </a>
           </div>
        )}
      </div>
    </article>
  );
}
