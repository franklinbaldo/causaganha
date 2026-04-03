import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { fetchAllData } from '../lib/fetchData';

type NetworkStatus = 'idle' | 'slow' | 'retrying' | 'error';

interface RetryDetail {
  attempt: number;
  maxRetries: number;
  delay: number;
}

export function NetworkStatusBanner() {
  const [status, setStatus] = useState<NetworkStatus>('idle');
  const [retryInfo, setRetryInfo] = useState<RetryDetail | null>(null);
  const [countdown, setCountdown] = useState<number>(0);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (status === 'retrying' && retryInfo && countdown > 0) {
      timer = setTimeout(() => setCountdown(c => c - 1000), 1000);
    }
    return () => clearTimeout(timer);
  }, [status, retryInfo, countdown]);

  useEffect(() => {
    const handleSlow = () => {
      if (status !== 'error' && status !== 'retrying') setStatus('slow');
    };

    const handleRetry = (e: Event) => {
      const detail = (e as CustomEvent<RetryDetail>).detail;
      setStatus('retrying');
      setRetryInfo(detail);
      setCountdown(detail.delay);
    };

    const handleError = () => {
      setStatus('error');
    };

    const handleSuccess = () => {
      setStatus('idle');
      setRetryInfo(null);
      setCountdown(0);
    };

    window.addEventListener('cg-network-slow', handleSlow);
    window.addEventListener('cg-network-retry', handleRetry);
    window.addEventListener('cg-network-error', handleError);
    window.addEventListener('cg-network-success', handleSuccess);

    return () => {
      window.removeEventListener('cg-network-slow', handleSlow);
      window.removeEventListener('cg-network-retry', handleRetry);
      window.removeEventListener('cg-network-error', handleError);
      window.removeEventListener('cg-network-success', handleSuccess);
    };
  }, [status]);

  if (status === 'idle') return null;

  const handleManualRetry = () => {
    setStatus('idle');
    setRetryInfo(null);
    setCountdown(0);
    // Trigger a refetch through the shared mechanism if possible,
    // or just fetchAllData which will update the shared cache eventually.
    // The safest is to rely on useDataRefresh's periodic fetch, but we can force one.
    fetchAllData().catch(console.error);
  };

  return (
    <div
      className={clsx(
        "fixed bottom-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm transition-all animate-fade-in",
        status === 'error' ? "bg-danger text-white" : "bg-warning-light text-black"
      )}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-center gap-3">
        {status === 'slow' && (
          <div>
            <p className="font-semibold text-sm">Slow Network Detected</p>
            <p className="text-xs opacity-80">Loading might take longer than usual. Using cached data if available.</p>
          </div>
        )}

        {status === 'retrying' && retryInfo && (
          <div>
            <p className="font-semibold text-sm">Connection Issue</p>
            <p className="text-xs opacity-80">
              Retrying (attempt {retryInfo.attempt}/{retryInfo.maxRetries}) in {Math.ceil(countdown / 1000)}s...
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="flex-1 flex items-center justify-between gap-4">
            <div>
              <p className="font-semibold text-sm">Network Failed</p>
              <p className="text-xs opacity-90">Could not connect to server. Showing cached offline data.</p>
            </div>
            <button
              onClick={handleManualRetry}
              className="px-3 py-1.5 bg-white text-danger text-xs font-bold rounded hover:bg-gray-100 transition-colors"
              aria-label="Retry network connection now"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
