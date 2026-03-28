import { useState, useEffect } from 'preact/compat';

export function LiveStatusWidget() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const fetchStatus = async () => {
      try {
        const resp = await fetch('https://archive.org/download/causaganha-live-status/status.json?t=' + new Date().getTime());
        if (!resp.ok) {
          throw new Error('Failed to fetch status');
        }
        const json = await resp.json();
        if (isMounted) {
          setData(json);
          setError(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(true);
        }
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  if (error) {
    return (
      <div className="card p-4 bg-gray-50 dark:bg-slate-900 border border-gray-100 dark:border-slate-800 flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-gray-400"></div>
        <span className="text-sm text-gray-500">Live pipeline status currently unavailable.</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card p-4 bg-gray-50 dark:bg-slate-900 border border-gray-100 dark:border-slate-800 flex items-center gap-3">
        <div className="w-4 h-4 rounded-full border-2 border-accent border-t-transparent animate-spin"></div>
        <span className="text-sm text-gray-500">Loading pipeline status...</span>
      </div>
    );
  }

  const { last_updated, zips_uploaded, active_tribunals, status } = data;
  const isRunning = status === 'running';

  // Check if really running based on last_updated (within 5 minutes)
  const lastUpdatedTime = new Date(last_updated);
  const now = new Date();
  const diffMinutes = (now - lastUpdatedTime) / 1000 / 60;
  const isActuallyRunning = isRunning && diffMinutes <= 5;

  return (
    <div className="card p-4 bg-white dark:bg-slate-900 border border-gray-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        {isActuallyRunning ? (
          <div className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-success"></span>
          </div>
        ) : (
          <div className={`w-3 h-3 rounded-full ${status === 'completed' ? 'bg-info' : 'bg-gray-400'}`}></div>
        )}
        <div>
          <h2 className="text-sm font-semibold text-black dark:text-white flex items-center gap-2">
            Pipeline {isActuallyRunning ? 'Running' : (status.charAt(0).toUpperCase() + status.slice(1))}
          </h2>
          <p className="text-xs text-gray-500">
            Updated {lastUpdatedTime.toLocaleTimeString()}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">ZIPs Uploaded</p>
          <p className="text-lg font-bold text-black dark:text-white">{zips_uploaded}</p>
        </div>
        <div className="w-px h-8 bg-gray-200 dark:bg-slate-700"></div>
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Active Tribunals</p>
          <p className="text-lg font-bold text-black dark:text-white">{active_tribunals}</p>
        </div>
      </div>
    </div>
  );
}
