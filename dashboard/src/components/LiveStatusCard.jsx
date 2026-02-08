import { Clock, CheckCircle, XCircle } from 'lucide-react';
import clsx from 'clsx';

export function LiveStatusCard({ stats }) {
  if (!stats) return <div className="cyber-card animate-pulse h-32"></div>;

  const isSuccess = stats.status === 'success';
  const statusColor = isSuccess ? 'text-cyber-primary' : 'text-cyber-danger';
  const borderColor = isSuccess ? 'border-cyber-primary' : 'border-cyber-danger';

  return (
    <div className={clsx("cyber-card relative overflow-hidden border-t-4", borderColor)}>
      <div className="flex justify-between items-start">
        <div role="status" aria-live="polite">
          <h2 className="text-sm text-cyber-muted uppercase tracking-widest mb-1.5 font-medium">System Status</h2>
          <div className="flex items-center gap-3">
            {isSuccess ? 
              <CheckCircle className="w-7 h-7 text-cyber-primary" aria-hidden="true" /> : 
              <XCircle className="w-7 h-7 text-cyber-danger" aria-hidden="true" />
            }
            <span className={clsx("text-3xl font-bold tracking-tight", statusColor)}>
              {isSuccess ? 'OPERATIONAL' : 'SYSTEM FAULT'}
            </span>
          </div>
          <div className="mt-3 text-sm text-cyber-muted flex flex-wrap items-center gap-x-6 gap-y-1 font-medium">
             <span className="flex items-center gap-1.5">
               <Clock className="w-4 h-4" aria-hidden="true" />
               Last Run: {new Date(stats.timestamp).toLocaleString()}
             </span>
             <span>ID: <span className="font-mono text-cyber-text">{stats.run_id}</span></span>
             <span>Duration: <span className="text-cyber-text">{stats.duration_seconds}s</span></span>
          </div>
          <span className="sr-only">
            System status: {isSuccess ? 'Operational' : 'System fault detected'}. Last run at {new Date(stats.timestamp).toLocaleString()}.
          </span>
        </div>

        {/* Mock Countdown - In real app, this would be calculated based on schedule */}
        <div className="text-right hidden sm:block">
             <div className="text-xs text-cyber-muted mb-1">NEXT RUN</div>
             <div className="text-2xl font-mono text-cyber-warning animate-pulse">~05:00</div>
        </div>
      </div>
    </div>
  );
}
