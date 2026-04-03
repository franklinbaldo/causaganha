import { useState, useEffect } from 'preact/compat';

interface DataSourceInfo {
  status: 'loading' | 'live' | 'fallback' | 'error';
  source: string | null;
  error: string | null;
  generated?: string;
}

export function DataSourceIndicator() {
  const [info, setInfo] = useState<DataSourceInfo>({ status: 'loading', source: null, error: null });

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
      } catch (err: unknown) {
        setInfo({ status: 'error', source: null, error: err instanceof Error ? err.message : String(err) });
      }
    }
    probe();
  }, []);

  return (
    <small role="status">
      <span className={info.status === 'live' ? 'cg-pulse' : undefined} />
      {info.status === 'loading' && 'Connecting...'}
      {info.status === 'live' && `Live via ${info.source} (${info.generated?.slice(0, 16)})`}
      {info.status === 'fallback' && `Static fallback (${info.source})`}
      {info.status === 'error' && `Offline: ${info.error}`}
    </small>
  );
}
