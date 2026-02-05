import { Calendar, TrendingDown, Clock, CheckCircle, AlertCircle, Loader } from 'lucide-react';

export function BackfillProgressCard({ progress }) {
  if (!progress) {
    return (
      <div className="bg-cyber-card border border-cyber-border p-6 rounded shadow-glow">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-cyber-primary" aria-hidden="true" />
          <h2 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
            Backfill Progress
          </h2>
        </div>
        <p className="text-cyber-muted text-xs">Loading...</p>
      </div>
    );
  }

  const {
    oldest_date,
    newest_date,
    unique_days,
    target_range,
    progress_pct,
    last_updated,
    status = 'unknown'
  } = progress;

  // Calculate ETA
  const calculateETA = () => {
    if (!progress_pct || progress_pct === 0) return 'N/A';

    // Assuming ~5 days processed per hour (rough estimate)
    const daysRemaining = target_range.total_days - unique_days;
    const hoursRemaining = Math.ceil(daysRemaining / 5);

    if (hoursRemaining < 1) return '< 1 hour';
    if (hoursRemaining < 24) return `~${hoursRemaining} hours`;
    const daysETA = Math.ceil(hoursRemaining / 24);
    return `~${daysETA} days`;
  };

  // Status indicator
  const getStatusInfo = () => {
    switch (status) {
      case 'advancing':
        return {
          icon: <CheckCircle className="w-4 h-4" aria-hidden="true" />,
          text: 'Advancing',
          color: 'text-cyber-primary',
          bg: 'bg-cyber-dim',
          ariaLabel: 'Status: Advancing - backfill is making progress'
        };
      case 'stuck':
        return {
          icon: <AlertCircle className="w-4 h-4" aria-hidden="true" />,
          text: 'Stuck',
          color: 'text-cyber-warning',
          bg: 'bg-cyber-warning/10',
          ariaLabel: 'Status: Stuck - backfill is stalled'
        };
      case 'starting':
        return {
          icon: <Loader className="w-4 h-4 animate-spin" aria-hidden="true" />,
          text: 'Starting',
          color: 'text-cyber-secondary',
          bg: 'bg-cyber-secondary/10',
          ariaLabel: 'Status: Starting - backfill is initializing'
        };
      default:
        return {
          icon: <AlertCircle className="w-4 h-4" aria-hidden="true" />,
          text: 'Unknown',
          color: 'text-cyber-muted',
          bg: 'bg-cyber-gray',
          ariaLabel: 'Status: Unknown'
        };
    }
  };

  const statusInfo = getStatusInfo();
  const eta = calculateETA();

  return (
    <div className="bg-cyber-card border border-cyber-border p-6 rounded shadow-glow">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-cyber-primary" aria-hidden="true" />
          <h2 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
            Backfill Progress
          </h2>
        </div>
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded ${statusInfo.bg}`}
          role="status"
          aria-label={statusInfo.ariaLabel}
        >
          <span className={statusInfo.color}>{statusInfo.icon}</span>
          <span className={`text-xs font-bold ${statusInfo.color}`}>
            {statusInfo.text}
          </span>
        </div>
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="border border-cyber-dim p-3 rounded bg-cyber-dark">
          <div className="flex items-center gap-2 mb-1">
            <TrendingDown className="w-4 h-4 text-cyber-secondary" aria-hidden="true" />
            <span className="text-xs text-cyber-muted uppercase tracking-wider font-medium">
              Oldest Date
            </span>
          </div>
          <div className="text-cyber-primary font-mono font-bold text-lg">
            {oldest_date || 'N/A'}
          </div>
        </div>

        <div className="border border-cyber-dim p-3 rounded bg-cyber-dark">
          <div className="flex items-center gap-2 mb-1">
            <Calendar className="w-4 h-4 text-cyber-secondary" aria-hidden="true" />
            <span className="text-xs text-cyber-muted uppercase tracking-wider font-medium">
              Newest Date
            </span>
          </div>
          <div className="text-cyber-primary font-mono font-bold text-lg">
            {newest_date || 'N/A'}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-cyber-muted">Coverage: {unique_days} days</span>
          <span className="text-xs text-cyber-primary font-bold">
            {progress_pct?.toFixed(2)}%
          </span>
        </div>
        <div
          className="w-full h-4 bg-cyber-dark border border-cyber-dim rounded-full overflow-hidden"
          role="progressbar"
          aria-valuenow={progress_pct || 0}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label={`Backfill progress: ${progress_pct?.toFixed(2)}%`}
        >
          <div
            className="h-full bg-gradient-to-r from-cyber-secondary to-cyber-primary transition-all duration-500 shadow-glow-lg"
            style={{ width: `${Math.min(progress_pct || 0, 100)}%` }}
          />
        </div>
        <div className="flex justify-between items-center mt-1">
          <span className="text-xs text-cyber-muted">
            {target_range.start}
          </span>
          <span className="text-xs text-cyber-muted">
            {unique_days} / {target_range.total_days} days
          </span>
          <span className="text-xs text-cyber-muted">
            {target_range.end}
          </span>
        </div>
      </div>

      {/* ETA */}
      <div className="flex items-center gap-2 text-xs">
        <Clock className="w-3 h-3 text-cyber-secondary" aria-hidden="true" />
        <span className="text-cyber-muted">ETA to completion:</span>
        <span className="text-cyber-primary font-bold">{eta}</span>
      </div>

      {/* Last Updated */}
      {last_updated && (
        <div className="mt-3 pt-3 border-t border-cyber-dim text-xs text-cyber-muted">
          Last updated: {new Date(last_updated).toLocaleString('pt-BR')}
        </div>
      )}
    </div>
  );
}
