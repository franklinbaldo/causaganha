import { useState, useEffect } from 'preact/compat';

export function DataSourceIndicator() {
  const [info, setInfo] = useState({ status: 'loading', source: null, error: null });

  useEffect(() => {
    async function probe() {
      const IA_URL = 'https://archive.org/download/causaganha-dashboard/meta.json';
      try {
        const res = await fetch(IA_URL);
        if (res.ok) {
          const data = await res.json();
          setInfo({
            status: 'live',
            source: 'Internet Archive',
            generated: data.generated_at,
            error: null,
          });
        } else {
          setInfo({ status: 'fallback', source: `IA HTTP ${res.status}`, error: null });
        }
      } catch (err) {
        setInfo({ status: 'error', source: null, error: err.message });
      }
    }
    probe();
  }, []);

  const colors = {
    loading: 'bg-gray-200 text-gray-600',
    live: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    fallback: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono ${colors[info.status]}`}>
      <span className={`w-2 h-2 rounded-full ${info.status === 'live' ? 'bg-green-500 animate-pulse' : info.status === 'error' ? 'bg-red-500' : 'bg-gray-400'}`} />
      {info.status === 'loading' && 'Connecting...'}
      {info.status === 'live' && `Live via ${info.source} (${info.generated?.slice(0, 16)})`}
      {info.status === 'fallback' && `Static fallback (${info.source})`}
      {info.status === 'error' && `Offline: ${info.error}`}
    </div>
  );
}
