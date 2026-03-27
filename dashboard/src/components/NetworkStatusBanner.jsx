import { useState, useEffect } from 'preact/compat';
import clsx from 'clsx';
import { abortSharedFetch } from '../lib/useDataRefresh';
import { fetchAllData } from '../lib/fetchData';

export function NetworkStatusBanner() {
  const [status, setStatus] = useState('idle'); // idle, slow, retrying, error
  const [retryInfo, setRetryInfo] = useState(null);
  const [countdown, setCountdown] = useState(0);

  useEffect(() => {
    let timer;
    if (status === 'retrying' && retryInfo && countdown > 0) {
      timer = setTimeout(() => setCountdown(c => c - 1000), 1000);
    }
    return () => clearTimeout(timer);
  }, [status, retryInfo, countdown]);

  useEffect(() => {
    const handleSlow = () => {
      if (status !== 'error' && status !== 'retrying') setStatus('slow');
    };

    const handleRetry = (e) => {
      setStatus('retrying');
      setRetryInfo(e.detail);
      setCountdown(e.detail.delay);
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

    // Dispatch a custom event to tell useDataRefresh components to immediately fetch again.
    // This allows the normal React state flow to update when the fetch succeeds.
    window.dispatchEvent(new CustomEvent('cg-network-manual-retry'));
  };

  const handleCancelRetry = () => {
    abortSharedFetch();
    setStatus('idle');
    setRetryInfo(null);
    setCountdown(0);
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
            <p className="font-semibold text-sm">Conexão Lenta</p>
            <p className="text-xs opacity-80">Usando dados em cache, se disponíveis.</p>
          </div>
        )}

        {status === 'retrying' && retryInfo && (
          <div className="flex-1 flex flex-col gap-2">
            <div>
              <p className="font-semibold text-sm">Problema de conexão</p>
              <p className="text-xs opacity-80">
                Tentando novamente ({retryInfo.attempt}/{retryInfo.maxRetries})... em {Math.ceil(countdown / 1000)}s
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleManualRetry}
                className="px-2 py-1 bg-black/10 hover:bg-black/20 text-xs font-bold rounded transition-colors"
              >
                Tentar agora
              </button>
              <button
                onClick={handleCancelRetry}
                className="px-2 py-1 bg-black/10 hover:bg-black/20 text-xs font-bold rounded transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="flex-1 flex items-center justify-between gap-4">
            <div>
              <p className="font-semibold text-sm">Falha na conexão</p>
              <p className="text-xs opacity-90">Não foi possível atualizar os dados. Exibindo versão offline.</p>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="px-3 py-1.5 bg-white text-danger text-xs font-bold rounded hover:bg-gray-100 transition-colors whitespace-nowrap"
            >
              Recarregar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
