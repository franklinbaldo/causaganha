import { useState, useEffect } from 'react';
import { Calendar, TrendingUp, Clock, AlertCircle, RefreshCw, Loader } from 'lucide-react';
import { SkeletonCard, SkeletonText, SkeletonLoader } from './SkeletonLoader';

// Skeleton Loading State
function DualProgressSkeleton() {
  return (
    <SkeletonCard>
      {/* Header skeleton */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <SkeletonLoader className="w-5 h-5 rounded" />
          <SkeletonText width="w-32" height="h-4" />
        </div>
        <SkeletonLoader className="w-20 h-6 rounded" />
      </div>

      {/* Two progress sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Section 1 skeleton */}
        <div className="space-y-4">
          <SkeletonText width="w-24" height="h-4" />
          <div className="space-y-3">
            <div className="flex justify-between">
              <SkeletonText width="w-20" height="h-4" />
              <SkeletonText width="w-12" height="h-4" />
            </div>
            <SkeletonLoader className="w-full h-4 rounded-full" />
            <div className="flex justify-between">
              <SkeletonText width="w-16" height="h-3" />
              <SkeletonText width="w-16" height="h-3" />
            </div>
          </div>
        </div>

        {/* Section 2 skeleton */}
        <div className="space-y-4">
          <SkeletonText width="w-28" height="h-4" />
          <div className="space-y-3">
            <div className="flex justify-between">
              <SkeletonText width="w-20" height="h-4" />
              <SkeletonText width="w-12" height="h-4" />
            </div>
            <SkeletonLoader className="w-full h-4 rounded-full" />
            <div className="flex justify-between">
              <SkeletonText width="w-16" height="h-3" />
              <SkeletonText width="w-16" height="h-3" />
            </div>
          </div>
        </div>
      </div>

      {/* Stats grid skeleton */}
      <div className="grid grid-cols-2 gap-4 mt-6">
        <div className="border border-cyber-border p-3 rounded bg-cyber-dark">
          <SkeletonText width="w-24" height="h-4" className="mb-2" />
          <SkeletonText width="w-20" height="h-6" />
        </div>
        <div className="border border-cyber-border p-3 rounded bg-cyber-dark">
          <SkeletonText width="w-24" height="h-4" className="mb-2" />
          <SkeletonText width="w-20" height="h-6" />
        </div>
      </div>
    </SkeletonCard>
  );
}

// Error State with Retry
function DualProgressError({ error, onRetry, retrying }) {
  return (
    <SkeletonCard>
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <AlertCircle className="w-12 h-12 text-cyber-danger mb-4 animate-pulse" aria-hidden="true" />
        <h3 className="text-cyber-danger font-bold text-sm tracking-widest uppercase mb-2">
          FETCH FAILED
        </h3>
        <p className="text-cyber-muted text-sm mb-6 max-w-md font-medium">
          {error || 'Unable to load progress data from Internet Archive API. This may be due to slow network or API timeout.'}
        </p>
        <button
          onClick={onRetry}
          disabled={retrying}
          aria-label="Retry fetching dashboard data"
          className="flex items-center gap-2 px-6 py-2 border border-cyber-primary text-cyber-primary hover:bg-cyber-primary hover:text-cyber-black transition-colors rounded uppercase text-xs tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {retrying ? (
            <>
              <Loader className="w-4 h-4 animate-spin" aria-hidden="true" />
              RETRYING...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
              RETRY
            </>
          )}
        </button>
      </div>
    </SkeletonCard>
  );
}

// Progress Section Component
function ProgressSection({ title, icon: Icon, progress, color = "primary" }) {
  const colorClasses = {
    primary: {
      text: "text-cyber-cyan",
      gradient: "from-cyber-cyan to-cyber-primary",
    },
    secondary: {
      text: "text-cyber-purple",
      gradient: "from-cyber-purple to-cyber-secondary",
    },
  };

  const colors = colorClasses[color] || colorClasses.primary;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Icon className={`w-5 h-5 ${colors.text}`} aria-hidden="true" />
        <h3 className={`${colors.text} font-bold text-sm tracking-widest uppercase`}>
          {title}
        </h3>
      </div>
      
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-base text-cyber-gray font-bold uppercase tracking-wider">{progress.label}</span>
          <span className={`text-lg font-bold ${colors.text}`}>
            {progress.percentage.toFixed(1)}%
          </span>
        </div>
        
        <div 
          className="w-full h-5 bg-cyber-dark border border-cyber-border rounded-full overflow-hidden"
          role="progressbar"
          aria-valuenow={progress.percentage}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label={`${title} progress: ${progress.percentage.toFixed(1)}%`}
        >
          <div
            className={`h-full bg-gradient-to-r ${colors.gradient} transition-all duration-500 shadow-glow-lg`}
            style={{ width: `${Math.min(progress.percentage, 100)}%` }}
          />
        </div>
        
        <div className="flex justify-between items-center mt-2">
          <span className="text-sm text-cyber-gray font-bold font-mono">
            {progress.current.toLocaleString()} / {progress.total.toLocaleString()}
          </span>
          <span className="text-sm text-cyber-gray font-bold uppercase tracking-widest">
            {progress.unit}
          </span>
        </div>
      </div>
    </div>
  );
}

export function DualProgressCard({ apiUrl = './dashboard-data.json', refreshInterval = 60000 }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retrying, setRetrying] = useState(false);

  const fetchData = async (isRetry = false) => {
    try {
      if (isRetry) {
        setRetrying(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await fetch(apiUrl);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const jsonData = await response.json();
      setData(jsonData);
    } catch (err) {
      console.error('Error fetching progress data:', err);
      setError(err.message || 'Failed to fetch data from Internet Archive API');
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    if (refreshInterval > 0) {
      const interval = setInterval(() => fetchData(), refreshInterval);
      return () => clearInterval(interval);
    }
  }, [apiUrl, refreshInterval]);

  // Loading state
  if (loading && !data) {
    return <DualProgressSkeleton />;
  }

  // Error state
  if (error && !data) {
    return (
      <DualProgressError 
        error={error} 
        onRetry={() => fetchData(true)} 
        retrying={retrying}
      />
    );
  }

  // No data fallback
  if (!data?.backfill_progress) {
    return (
      <SkeletonCard>
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-cyber-primary" />
          <h2 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
            Pipeline Progress
          </h2>
        </div>
        <p className="text-cyber-muted text-sm">No data available</p>
      </SkeletonCard>
    );
  }

  const cp = data.collect_progress || data.backfill_progress || {};
  const consP = data.consolidate_progress || {};

  const {
    unique_days = 0,
    target_range = {},
    progress_pct = 0,
    total_items = 0,
    oldest_date,
    newest_date,
    last_updated,
  } = cp;

  const collectProgress = {
    label: 'Days Collected',
    current: unique_days,
    total: target_range.total_days || 764,
    percentage: progress_pct,
    unit: 'days',
  };

  const consUniqueDays = consP.unique_days || 0;
  const consTotalDays = consP.target_range?.total_days || target_range.total_days || 764;
  const consPct = consP.progress_pct || (consTotalDays > 0 ? (consUniqueDays / consTotalDays) * 100 : 0);

  const consolidateProgress = {
    label: 'Days Consolidated',
    current: consUniqueDays,
    total: consTotalDays,
    percentage: consPct,
    unit: 'days',
  };

  return (
    <SkeletonCard>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Calendar className="w-5 h-5 text-cyber-primary" />
          <h2 className="text-cyber-primary font-bold text-sm tracking-widest uppercase">
            Pipeline Progress
          </h2>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-cyber-dim border border-cyber-primary/30">
          <span className="w-2.5 h-2.5 bg-cyber-primary rounded-full animate-pulse" />
          <span className="text-sm font-bold text-cyber-primary">ACTIVE</span>
        </div>
      </div>

      {/* Dual Progress Bars */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <ProgressSection
          title="Collection"
          icon={Calendar}
          progress={collectProgress}
          color="primary"
        />
        <ProgressSection
          title="Consolidation"
          icon={TrendingUp}
          progress={consolidateProgress}
          color="secondary"
        />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="border border-cyber-border p-3 rounded bg-cyber-dark">
          <div className="flex items-center gap-2 mb-1">
            <Calendar className="w-4 h-4 text-cyber-cyan" aria-hidden="true" />
            <span className="text-sm text-cyber-gray uppercase tracking-wider font-medium">
              Date Range
            </span>
          </div>
          <div className="text-cyber-cyan font-mono font-bold text-base">
            {oldest_date && newest_date ? (
              <span className="text-sm">
                {oldest_date} → {newest_date}
              </span>
            ) : (
              'N/A'
            )}
          </div>
        </div>

        <div className="border border-cyber-border p-3 rounded bg-cyber-dark">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-cyber-purple" aria-hidden="true" />
            <span className="text-sm text-cyber-gray uppercase tracking-wider font-medium">
              Total Items
            </span>
          </div>
          <div className="text-cyber-purple font-mono font-bold text-base">
            {total_items.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Last Updated */}
      {last_updated && (
        <div className="mt-3 pt-3 border-t border-cyber-border flex justify-between items-center">
          <span className="text-sm text-cyber-gray font-medium">
            Last updated: {new Date(last_updated).toLocaleString('pt-BR')}
          </span>
          <button
            onClick={() => fetchData(true)}
            disabled={retrying}
            className="text-cyber-primary hover:text-cyber-secondary transition-colors disabled:opacity-50"
            title="Refresh data"
          >
            <RefreshCw className={`w-3 h-3 ${retrying ? 'animate-spin' : ''}`} />
          </button>
        </div>
      )}
    </SkeletonCard>
  );
}
