import { useState, useEffect } from 'preact/compat';
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
    if (status === 'retrying' && retryInfo && countdown> 0) {
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
    <aside
      role="alert"
      aria-live="assertive">
      {status === 'slow' && (
        <div>
          <strong>Rede Lenta Detectada</strong>
          <small>O carregamento pode demorar mais que o normal. Usando dados em cache, se disponíveis.</small>
        </div>
      )}

      {status === 'retrying' && retryInfo && (
        <div>
          <strong>Problema de Conexão</strong>
          <small>
            Tentando novamente (tentativa {retryInfo.attempt}/{retryInfo.maxRetries}) em {Math.ceil(countdown / 1000)}s...
          </small>
        </div>
      )}

      {status === 'error' && (
        <div>
          <div>
            <strong>Falha na Rede</strong>
            <small>Não foi possível conectar ao servidor. Mostrando dados offline em cache.</small>
          </div>
          <button
            className="outline"
            onClick={handleManualRetry}
            aria-label="Tentar reconectar rede agora">
            Tentar Novamente
          </button>
        </div>
      )}
    </aside>
  );
}
