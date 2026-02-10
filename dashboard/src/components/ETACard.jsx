import { Clock, TrendingUp, Target, AlertTriangle, Zap } from 'lucide-react';

/**
 * Calculate velocity and ETA from backfill progress data
 */
function calculateETA(backfillProgress) {
  if (!backfillProgress) {
    return { velocity: 0, etaDays: null, status: 'no-data' };
  }

  // Handle both the legacy backfill_progress object and the newer full data object
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

  // Use recent_activity for velocity if available (last 7-14 days)
  const activityData = recent_activity.length > 0 ? recent_activity : daily_stats.slice(-14);

  if (activityData.length === 0) {
    return { velocity: 0, etaDays: null, remainingDays, totalDays, uniqueDays: unique_days, status: 'no-activity' };
  }

  // Calculate average items per day from recent activity
  const totalItemsRecent = activityData.reduce((sum, d) => sum + (d.count || 0), 0);
  const avgItemsPerDay = totalItemsRecent / activityData.length;

  // Calculate "Day Velocity": how many unique days we are completing per actual day
  // Since we have 91 tribunals, each day-tribunal pair is a unit.
  // total_units = totalDays * 91
  // units_done = unique_days * 91 (approximate, if we assume uniform progress)
  // But wait, the better way is to see how many items we process per calendar day.
  
  const itemsPerUniqueDayEstimate = unique_days > 0 
    ? (total_items || 0) / unique_days 
    : 91; // Fallback: 91 tribunals * 1 item/day

  // Velocity in terms of "calendar days completed per day"
  const daysVelocity = avgItemsPerDay / itemsPerUniqueDayEstimate;

  let etaDays = daysVelocity > 0 ? Math.ceil(remainingDays / daysVelocity) : null;

  // Consider per-tribunal variance if tribunalStats available
  // tribunal_stats count in generate-data.py is actually the number of days collected for that tribunal
  if (tribunalStats.length > 0) {
    const slowestTribunal = tribunalStats.reduce((min, t) => (t.count < min.count ? t : min), tribunalStats[0]);
    const slowestCount = slowestTribunal.count;
    const slowestRemaining = Math.max(0, totalDays - slowestCount);
    
    // If we assume all tribunals are processed at roughly the same velocity (which is sharing the total velocity)
    // The bottleneck is the tribunal with the most remaining days.
    const tribunalVelocity = daysVelocity / 91; // Average velocity per tribunal
    const slowestEtaDays = tribunalVelocity > 0 ? Math.ceil(slowestRemaining / tribunalVelocity) : etaDays;
    
    // Use the more conservative (larger) ETA
    if (slowestEtaDays > (etaDays || 0)) {
        etaDays = slowestEtaDays;
    }
  }

  // Determine status
  let status = 'active';
  if (avgItemsPerDay === 0) status = 'stalled';
  else if (etaDays && etaDays > 180) status = 'slow';
  else if (remainingDays <= 0) status = 'complete';

  return {
    velocity: Math.round(avgItemsPerDay),
    daysVelocity: daysVelocity.toFixed(2),
    etaDays,
    remainingDays,
    totalDays,
    uniqueDays: unique_days,
    progressPct: progress.progress_pct || (unique_days / totalDays * 100),
    totalItems: total_items,
    status,
  };
}

/**
 * Format ETA in human-readable form
 */
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

/**
 * Get completion date estimate
 */
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

export function ETACard({ backfillProgress }) {
  const eta = calculateETA(backfillProgress);

  const statusConfig = {
    'complete': {
      icon: Target,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/50',
      label: 'COMPLETE',
    },
    'active': {
      icon: Zap,
      color: 'text-cyber-primary',
      bgColor: 'bg-cyber-primary/10',
      borderColor: 'border-cyber-primary/50',
      label: 'ON TRACK',
    },
    'slow': {
      icon: Clock,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/10',
      borderColor: 'border-yellow-500/50',
      label: 'SLOW',
    },
    'stalled': {
      icon: AlertTriangle,
      color: 'text-cyber-danger',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/50',
      label: 'STALLED',
    },
    'no-data': {
      icon: AlertTriangle,
      color: 'text-cyber-muted',
      bgColor: 'bg-cyber-dark',
      borderColor: 'border-cyber-border',
      label: 'NO DATA',
    },
    'no-activity': {
      icon: Clock,
      color: 'text-cyber-muted',
      bgColor: 'bg-cyber-dark',
      borderColor: 'border-cyber-border',
      label: 'AWAITING',
    },
  };

  const config = statusConfig[eta.status] || statusConfig['no-data'];
  const StatusIcon = config.icon;
  const completionDate = getCompletionDate(eta.etaDays);

  return (
    <div className={`border ${config.borderColor} ${config.bgColor} p-4 rounded bg-cyber-dark/50`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock className={`w-5 h-5 ${config.color}`} />
          <h3 className={`${config.color} font-bold text-sm uppercase tracking-wider`}>
            Completion ETA
          </h3>
        </div>
        <div className={`text-[10px] font-bold px-2 py-0.5 rounded border ${config.borderColor} ${config.color}`}>
          {config.label}
        </div>
      </div>

      {/* Main ETA Display */}
      <div className="text-center mb-6">
        <div className="text-cyber-muted text-xs uppercase mb-1">
          Estimated Time Remaining
        </div>
        <div className={`text-4xl font-bold ${config.color} font-mono mb-2`}>
          {formatETA(eta.etaDays)}
        </div>
        {completionDate && (
          <div className="text-sm text-cyber-gray">
            Target Date: <span className="text-white">{completionDate}</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="border border-cyber-border p-2 rounded">
          <div className="text-[10px] text-cyber-gray uppercase mb-1">Velocity</div>
          <div className="text-cyber-cyan font-mono font-bold">
            {eta.velocity > 0 ? `${eta.velocity}/d` : '--'}
          </div>
        </div>

        <div className="border border-cyber-border p-2 rounded">
          <div className="text-[10px] text-cyber-gray uppercase mb-1">Remaining</div>
          <div className="text-cyber-purple font-mono font-bold">
            {eta.remainingDays > 0 ? `${eta.remainingDays}d` : 'DONE'}
          </div>
        </div>

        <div className="border border-cyber-border p-2 rounded">
          <div className="text-[10px] text-cyber-gray uppercase mb-1">Progress</div>
          <div className="text-cyber-secondary font-mono font-bold">
            {eta.progressPct?.toFixed(1) || 0}%
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="mt-4">
        <div className="flex justify-between text-xs text-cyber-gray mb-1">
          <span>{eta.uniqueDays || 0} days</span>
          <span>{Math.min(eta.progressPct || 0, 100).toFixed(1)}%</span>
        </div>
        <div className="w-full h-2 bg-cyber-black border border-cyber-border rounded-full overflow-hidden">
          <div
            className="h-full bg-cyber-primary transition-all duration-500"
            style={{ width: `${Math.min(eta.progressPct || 0, 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
