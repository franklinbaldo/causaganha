import { useDataRefresh } from '../lib/useDataRefresh';

const TargetIcon = ({ className }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
  </svg>
);

/**
 * Calculate velocity and ETA from backfill progress data.
 * Preserves the exact algorithm from the original ETACard.
 */
function calculateETA(backfillProgress) {
  if (!backfillProgress) {
    return { velocity: 0, etaDays: null, status: 'no-data' };
  }

  const progress = backfillProgress.backfill_progress || backfillProgress;
  const tribunalStats = backfillProgress.tribunal_stats || [];

  const {
    unique_days = 0,
    target_range = {},
    daily_stats = [],
    recent_activity = [],
    total_items = 0,
  } = progress;

  const totalDays = target_range.total_days || 764;
  const remainingDays = Math.max(0, totalDays - unique_days);

  const activityData = recent_activity.length > 0 ? recent_activity : daily_stats.slice(-14);

  if (activityData.length === 0) {
    return { velocity: 0, etaDays: null, remainingDays, totalDays, uniqueDays: unique_days, status: 'no-activity' };
  }

  const totalItemsRecent = activityData.reduce((sum, d) => sum + (d.count || 0), 0);
  const avgItemsPerDay = totalItemsRecent / activityData.length;

  const itemsPerUniqueDayEstimate = unique_days > 0
    ? (total_items || 0) / unique_days
    : 91;

  const daysVelocity = avgItemsPerDay / itemsPerUniqueDayEstimate;

  let etaDays = daysVelocity > 0 ? Math.ceil(remainingDays / daysVelocity) : null;

  if (tribunalStats.length > 0) {
    const slowestTribunal = tribunalStats.reduce((min, t) => (t.count < min.count ? t : min), tribunalStats[0]);
    const slowestCount = slowestTribunal.count;
    const slowestRemaining = Math.max(0, totalDays - slowestCount);

    const tribunalVelocity = daysVelocity / 91;
    const slowestEtaDays = tribunalVelocity > 0 ? Math.ceil(slowestRemaining / tribunalVelocity) : etaDays;

    if (slowestEtaDays > (etaDays || 0)) {
      etaDays = slowestEtaDays;
    }
  }

  let status = 'active';
  if (avgItemsPerDay === 0) status = 'stalled';
  else if (etaDays && etaDays > 180) status = 'slow';
  else if (remainingDays <= 0) status = 'complete';

  return {
    velocity: Math.round(avgItemsPerDay),
    daysVelocity: Math.round(daysVelocity * 100) / 100,
    etaDays,
    remainingDays,
    totalDays,
    uniqueDays: unique_days,
    progressPct: progress.progress_pct || (unique_days / totalDays * 100),
    totalItems: total_items,
    status,
  };
}

function formatETA(days) {
  if (days === null || days === undefined) return 'Unknown';
  if (days <= 0) return 'Complete!';
  if (days === 1) return '1 day';
  if (days < 7) return `${days} days`;
  if (days < 30) {
    const weeks = Math.round(days / 7);
    return `~${weeks} week${weeks > 1 ? 's' : ''}`;
  }
  if (days < 365) {
    const months = Math.round(days / 30);
    return `~${months} month${months > 1 ? 's' : ''}`;
  }
  const years = (days / 365).toFixed(1);
  return `~${years} years`;
}

function getCompletionDate(etaDays) {
  if (etaDays === null || etaDays <= 0) return null;
  const date = new Date();
  date.setDate(date.getDate() + etaDays);
  return date.toLocaleDateString('pt-BR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

const statusConfig = {
  'complete': { color: 'text-success', bgColor: 'bg-success-muted', label: 'Complete' },
  'active': { color: 'text-accent', bgColor: 'bg-accent-muted', label: 'On Track' },
  'slow': { color: 'text-warning', bgColor: 'bg-warning-muted', label: 'Slow' },
  'stalled': { color: 'text-danger', bgColor: 'bg-danger-muted', label: 'Stalled' },
  'no-data': { color: 'text-content-tertiary', bgColor: 'bg-surface-overlay', label: 'No Data' },
  'no-activity': { color: 'text-content-tertiary', bgColor: 'bg-surface-overlay', label: 'Awaiting' },
};

function ProgressBar({ label, current, total, percentage, color = 'accent', sublabel }) {
  const colorMap = {
    accent: 'bg-accent',
    purple: 'bg-purple',
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-sm font-medium text-content-secondary">{label}</span>
        <span className="text-sm font-semibold font-mono text-content tabular-nums">
          {percentage.toFixed(1)}%
        </span>
      </div>
      <div
        className="w-full h-4 bg-surface-overlay border border-border-muted rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin="0"
        aria-valuemax="100"
        aria-label={`${label} progress: ${percentage.toFixed(1)}%`}
      >
        <div
          className={`h-full ${colorMap[color] || 'bg-accent'} rounded-full transition-all duration-700`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-xs text-content-tertiary font-mono tabular-nums">
          {current.toLocaleString()} / {total.toLocaleString()} days
        </span>
        {sublabel && (
          <span className="text-xs text-content-tertiary">
            {sublabel}
          </span>
        )}
      </div>
    </div>
  );
}

function BackfillHeroSkeleton() {
  return (
    <div className="card">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-surface-overlay animate-pulse" />
        <div>
          <div className="w-40 h-6 bg-surface-overlay rounded animate-pulse" />
          <div className="w-24 h-4 bg-surface-overlay rounded animate-pulse mt-1" />
        </div>
      </div>
      <div className="w-full h-20 bg-surface-overlay rounded-lg animate-pulse mb-6" />
      <div className="grid grid-cols-4 gap-3">
        {[0, 1, 2, 3].map(i => (
          <div key={i}>
            <div className="w-16 h-3 bg-surface-overlay rounded animate-pulse mb-2" />
            <div className="w-20 h-7 bg-surface-overlay rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function BackfillHero({ initialData }) {
  const { data: backfillProgress } = useDataRefresh('effectiveBackfill', initialData);

  if (!backfillProgress) {
    return <BackfillHeroSkeleton />;
  }

  const eta = calculateETA(backfillProgress);
  const config = statusConfig[eta.status] || statusConfig['no-data'];
  const completionDate = getCompletionDate(eta.etaDays);

  // Collection & consolidation progress
  const cp = backfillProgress.collect_progress || backfillProgress.backfill_progress || {};
  const consP = backfillProgress.consolidate_progress || {};

  const collectPct = cp.progress_pct || 0;
  const collectDays = cp.unique_days || 0;
  const collectTotal = cp.target_range?.total_days || 764;

  const consDays = consP.unique_days || 0;
  const consTotal = consP.target_range?.total_days || collectTotal;
  const consPct = consP.progress_pct || (consTotal > 0 ? (consDays / consTotal) * 100 : 0);

  // Consolidation lag: days collected but not yet consolidated
  const consolidationLag = Math.max(0, collectDays - consDays);

  // Tribunal coverage summary
  const tribunalStats = backfillProgress.tribunal_stats || [];
  const tribunalsWithGoodCoverage = tribunalStats.filter(t => t.data_rate_pct >= 90).length;
  const totalTribunals = tribunalStats.length || 91;

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${config.bgColor}`}>
            <TargetIcon className={`w-5 h-5 ${config.color}`} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-content">Backfill Progress</h2>
            <p className="text-sm text-content-tertiary">
              {cp.oldest_date && cp.newest_date
                ? `${cp.oldest_date} to ${cp.newest_date}`
                : 'Overall completion status'}
            </p>
          </div>
        </div>
        <span className={`badge ${config.bgColor} ${config.color}`}>
          {config.label}
        </span>
      </div>

      {/* Main metric: progress percentage */}
      <div className="text-center mb-6 py-4 bg-surface rounded-xl">
        <div className="stat-label mb-1">Overall Progress</div>
        <div className={`text-5xl font-bold font-mono tabular-nums ${config.color} mb-1`}>
          {(eta.progressPct || 0).toFixed(1)}%
        </div>
        <div className="text-sm text-content-secondary">
          {eta.status !== 'no-data' && eta.status !== 'no-activity' && (
            <>
              ETA: <span className="font-semibold text-content">{formatETA(eta.etaDays)}</span>
              {completionDate && (
                <span className="text-content-tertiary ml-1">({completionDate})</span>
              )}
            </>
          )}
        </div>
      </div>

      {/* Stats row - 4 columns with more meaningful data */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="text-center p-3 bg-surface rounded-lg">
          <div className="stat-label mb-1">Velocity</div>
          <div className="text-xl font-semibold font-mono tabular-nums text-accent">
            {eta.velocity > 0 ? `${eta.velocity}/d` : '--'}
          </div>
          <div className="text-[10px] text-content-tertiary mt-0.5">tribunals/day</div>
        </div>
        <div className="text-center p-3 bg-surface rounded-lg">
          <div className="stat-label mb-1">Days/d</div>
          <div className="text-xl font-semibold font-mono tabular-nums text-accent">
            {eta.daysVelocity > 0 ? eta.daysVelocity : '--'}
          </div>
          <div className="text-[10px] text-content-tertiary mt-0.5">unique days/day</div>
        </div>
        <div className="text-center p-3 bg-surface rounded-lg">
          <div className="stat-label mb-1">Remaining</div>
          <div className="text-xl font-semibold font-mono tabular-nums text-purple">
            {eta.remainingDays > 0 ? `${eta.remainingDays}d` : 'Done'}
          </div>
          <div className="text-[10px] text-content-tertiary mt-0.5">of {eta.totalDays}d total</div>
        </div>
        <div className="text-center p-3 bg-surface rounded-lg">
          <div className="stat-label mb-1">Cons. Lag</div>
          <div className={`text-xl font-semibold font-mono tabular-nums ${consolidationLag > 10 ? 'text-warning' : 'text-success'}`}>
            {consolidationLag}d
          </div>
          <div className="text-[10px] text-content-tertiary mt-0.5">awaiting parquet</div>
        </div>
      </div>

      {/* Dual progress bars */}
      <div className="space-y-4">
        <ProgressBar
          label="Collection"
          current={collectDays}
          total={collectTotal}
          percentage={collectPct}
          color="accent"
          sublabel={`${(eta.totalItems || 0).toLocaleString()} tribunal-days`}
        />
        <ProgressBar
          label="Consolidation"
          current={consDays}
          total={consTotal}
          percentage={consPct}
          color="purple"
          sublabel={consolidationLag > 0 ? `${consolidationLag} days pending` : 'up to date'}
        />
      </div>

      {/* Tribunal coverage summary */}
      {tribunalStats.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border-muted flex items-center justify-between text-xs text-content-tertiary">
          <span>
            Tribunal coverage: <span className="font-mono font-medium text-content">{tribunalsWithGoodCoverage}/{totalTribunals}</span> with {'>'}90% data rate
          </span>
          {cp.last_updated && (
            <span>Updated {new Date(cp.last_updated).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
          )}
        </div>
      )}
    </div>
  );
}
