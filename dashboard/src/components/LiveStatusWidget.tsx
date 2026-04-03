import { useState, useEffect } from 'preact/compat';

interface LiveStatusData {
  last_updated: string;
  zips_uploaded: number;
  active_tribunals: number;
  status: string;
}

const NTFY_TOPIC = 'causaganha-a7f3b2e9c1d4';
const NTFY_SSE_URL = `https://ntfy.sh/${NTFY_TOPIC}/sse`;
const NTFY_POLL_URL = `https://ntfy.sh/${NTFY_TOPIC}/json?poll=1&since=1h`;
const IA_FALLBACK_URL = 'https://archive.org/download/causaganha-live-status/status.json';

export function LiveStatusWidget() {
  const [data, setData] = useState<LiveStatusData | null>(null);
  const [error, setError] = useState<boolean>(false);
  const [source, setSource] = useState<'loading' | 'ntfy-sse' | 'polling'>('loading');
  const [now, setNow] = useState<number>(() => Date.now());

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    let isMounted = true;
    let es: EventSource | null = null;
    let fallbackInterval: ReturnType<typeof setInterval> | null = null;

    const applyMessage = (msgStr: string) => {
      try {
        const parsed: LiveStatusData = JSON.parse(msgStr);
        if (isMounted) {
          setData(parsed);
          setError(false);
        }
      } catch { /* ignore parse errors */ }
    };

    // Try ntfy SSE first (real-time push)
    const startSSE = () => {
      try {
        es = new EventSource(NTFY_SSE_URL);
        es.onopen = () => {
          if (isMounted) setSource('ntfy-sse');
        };
        es.onmessage = (e: MessageEvent) => {
          try {
            const envelope = JSON.parse(e.data);
            if (envelope.event === 'message' && envelope.message) {
              applyMessage(envelope.message);
            }
          } catch { /* ignore parse errors */ }
        };
        es.onerror = () => {
          es!.close();
          startFallback();
        };
      } catch {
        startFallback();
      }
    };

    // Fallback: poll ntfy JSON endpoint, then IA
    const startFallback = () => {
      if (!isMounted) return;
      setSource('polling');

      const poll = async () => {
        // Try ntfy poll first
        try {
          const resp = await fetch(NTFY_POLL_URL);
          if (resp.ok) {
            const text = await resp.text();
            const lines = text.trim().split('\n').filter(Boolean);
            if (lines.length > 0) {
              const last = JSON.parse(lines[lines.length - 1]);
              applyMessage(last.message);
              return;
            }
          }
        } catch { /* ignore poll errors */ }

        // Last resort: IA static file
        try {
          const resp = await fetch(IA_FALLBACK_URL + '?t=' + performance.now());
          if (resp.ok) {
            const json: LiveStatusData = await resp.json();
            if (isMounted) {
              setData(json);
              setError(false);
            }
          }
        } catch {
          if (isMounted) setError(true);
        }
      };

      poll();
      fallbackInterval = setInterval(poll, 60000);
    };

    // Load latest on mount via ntfy poll (before SSE connects)
    fetch(NTFY_POLL_URL)
      .then((r) => r.ok ? r.text() : Promise.reject())
      .then((text) => {
        const lines = text.trim().split('\n').filter(Boolean);
        if (lines.length > 0) {
          const last = JSON.parse(lines[lines.length - 1]);
          applyMessage(last.message);
        }
      })
      .catch(() => {});

    startSSE();

    return () => {
      isMounted = false;
      if (es) es.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
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
  const lastUpdatedTime = new Date(last_updated);
  const diffMinutes = (now - lastUpdatedTime.getTime()) / 1000 / 60;
  const isActuallyRunning = status === 'running' && diffMinutes <= 5;

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
            Pipeline {isActuallyRunning ? 'Running' : (status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown')}
            {source === 'ntfy-sse' && (
              <span className="text-xs font-normal text-gray-400">● live</span>
            )}
          </h2>
          <p className="text-xs text-gray-500">
            Updated {lastUpdatedTime.toLocaleTimeString()}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">ZIPs Uploaded</p>
          <p className="text-lg font-bold text-black dark:text-white">{zips_uploaded ?? '—'}</p>
        </div>
        <div className="w-px h-8 bg-gray-200 dark:bg-slate-700"></div>
        <div className="text-center">
          <p className="text-xs text-gray-500 mb-1">Active Tribunals</p>
          <p className="text-lg font-bold text-black dark:text-white">{active_tribunals ?? '—'}</p>
        </div>
      </div>
    </div>
  );
}
