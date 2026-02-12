import { Clock, CheckCircle, XCircle, Activity } from 'lucide-react';
import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { SkeletonLoader, SkeletonText } from './SkeletonLoader';

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

export function LiveStatusCard({ stats, cacheToday }) {
  const countdown = useNextRunCountdown(stats?.timestamp);

  if (!stats) return (
    <div className="cyber-card h-32 border-t-4 border-cyber-border">
       <div className="flex justify-between items-start">
         <div className="w-full">
           <SkeletonText width="w-32" height="h-4" className="mb-2" />
           <div className="flex items-center gap-3">
             <SkeletonLoader className="w-8 h-8 rounded-full" />
             <SkeletonText width="w-64" height="h-10" />
           </div>
           <div className="mt-4 flex gap-4">
             <SkeletonText width="w-48" height="h-4" />
             <SkeletonText width="w-32" height="h-4" />
           </div>
         </div>
       </div>
    </div>
  );

  const isSuccess = stats.status === 'success';
  const statusColor = isSuccess ? 'text-cyber-primary' : 'text-cyber-danger';
  const borderColor = isSuccess ? 'border-cyber-primary' : 'border-cyber-danger';
  const health = cacheToday?.health;
  const filesToday = cacheToday?.files_today;

  return (
    <div className={clsx("cyber-card relative overflow-hidden border-t-4", borderColor)}>
      <div className="flex justify-between items-start">
        <div role="status" aria-live="polite">
          <h2 className="text-base text-cyber-gray uppercase tracking-widest mb-1.5 font-medium">System Status</h2>
          <div className="flex items-center gap-3">
            {isSuccess ?
              <CheckCircle className="w-7 h-7 text-cyber-primary" aria-hidden="true" /> :
              <XCircle className="w-7 h-7 text-cyber-danger" aria-hidden="true" />
            }
            <span className={clsx("text-3xl font-bold tracking-tight", statusColor)}>
              {isSuccess ? 'OPERATIONAL' : 'SYSTEM FAULT'}
            </span>
          </div>
          <div className="mt-3 text-base text-cyber-gray flex flex-wrap items-center gap-x-6 gap-y-2 font-bold uppercase tracking-wide">
             <span className="flex items-center gap-1.5">
               <Clock className="w-5 h-5" aria-hidden="true" />
               Last Run: {new Date(stats.timestamp).toLocaleString()}
             </span>
             <span>Duration: <span className="text-cyber-text">{stats.duration_seconds}s</span></span>
             {health != null && (
               <span className="flex items-center gap-1.5">
                 <Activity className="w-5 h-5" aria-hidden="true" />
                 Health: <span className={clsx(health >= 70 ? "text-cyber-primary" : "text-cyber-danger")}>{health}%</span>
               </span>
             )}
             {filesToday != null && (
               <span>Today: <span className="text-cyber-text">{filesToday}/91</span> tribunais</span>
             )}
          </div>
          <span className="sr-only">
            System status: {isSuccess ? 'Operational' : 'System fault detected'}. Last run at {new Date(stats.timestamp).toLocaleString()}.
          </span>
        </div>

        <div className="text-right hidden sm:block">
             <div className="text-sm text-cyber-gray mb-1 font-medium">NEXT RUN</div>
             <div className="text-2xl font-mono text-cyber-warning animate-pulse">{countdown}</div>
        </div>
      </div>
    </div>
  );
}
