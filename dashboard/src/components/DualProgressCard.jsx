import { Calendar, Download, Package } from 'lucide-react';

export function DualProgressCard({ collectProgress, consolidateProgress }) {
  const renderProgress = (progress, label, icon, color) => {
    if (!progress) {
      return (
        <div className="bg-cyber-dark border border-cyber-dim p-4 rounded">
          <div className="flex items-center gap-2 mb-3">
            {icon}
            <h3 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
              {label}
            </h3>
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
    } = progress;

    return (
      <div className="bg-cyber-dark border border-cyber-dim p-4 rounded">
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          {icon}
          <h3 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
            {label}
          </h3>
        </div>

        {/* Date Range - Compact */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          <div className="border border-cyber-dim/50 p-2 rounded bg-cyber-dark/50">
            <div className="text-xs text-cyber-muted uppercase tracking-wider mb-1">
              Oldest
            </div>
            <div className={`font-mono font-bold text-sm ${color}`}>
              {oldest_date || 'N/A'}
            </div>
          </div>

          <div className="border border-cyber-dim/50 p-2 rounded bg-cyber-dark/50">
            <div className="text-xs text-cyber-muted uppercase tracking-wider mb-1">
              Newest
            </div>
            <div className={`font-mono font-bold text-sm ${color}`}>
              {newest_date || 'N/A'}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-cyber-muted">{unique_days} days</span>
            <span className={`text-xs font-bold ${color}`}>
              {progress_pct?.toFixed(2)}%
            </span>
          </div>
          <div
            className="w-full h-4 bg-cyber-dark border border-cyber-dim rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={progress_pct || 0}
            aria-valuemin="0"
            aria-valuemax="100"
            aria-label={`${label} progress: ${progress_pct?.toFixed(1)}%`}
          >
            <div
              className={`h-full transition-all duration-500 ${
                color === 'text-cyan-400' 
                  ? 'bg-gradient-to-r from-cyan-500 to-cyan-400' 
                  : 'bg-gradient-to-r from-purple-500 to-purple-400'
              }`}
              style={{ width: `${Math.min(progress_pct || 0, 100)}%` }}
            />
          </div>
          <div className="flex justify-between items-center mt-1">
            <span className="text-xs text-cyber-muted">
              {target_range?.start || '2024-01-01'}
            </span>
            <span className="text-xs text-cyber-muted">
              {unique_days} / {target_range?.total_days || 765}
            </span>
            <span className="text-xs text-cyber-muted">
              {target_range?.end || '2026-02-03'}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-cyber-card border border-cyber-border p-6 rounded shadow-glow">
      {/* Main Header */}
      <div className="flex items-center gap-2 mb-6">
        <Calendar className="w-5 h-5 text-cyber-primary" aria-hidden="true" />
        <h2 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
          Pipeline Progress
        </h2>
      </div>

      {/* Two Progress Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {renderProgress(
          collectProgress,
          '📥 Download',
          <Download className="w-5 h-5 text-cyan-400" aria-hidden="true" />,
          'text-cyan-400'
        )}
        {renderProgress(
          consolidateProgress,
          '📦 Consolidation',
          <Package className="w-5 h-5 text-purple-400" aria-hidden="true" />,
          'text-purple-400'
        )}
      </div>

      {/* Last Updated */}
      {(collectProgress?.last_updated || consolidateProgress?.last_updated) && (
        <div className="mt-4 pt-4 border-t border-cyber-dim text-xs text-cyber-muted text-center">
          Last updated: {new Date(
            collectProgress?.last_updated || consolidateProgress?.last_updated
          ).toLocaleString('pt-BR')}
        </div>
      )}
    </div>
  );
}
