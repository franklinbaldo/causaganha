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
            if (lines.length> 0) {
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
        if (lines.length> 0) {
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
      <article>
        <span>Status ao vivo indisponível.</span>
      </article>
    );
  }

  if (!data) {
    return (
      <article>
        <span aria-busy="true">Carregando status do pipeline...</span>
      </article>
    );
  }

  const { last_updated, zips_uploaded, active_tribunals, status } = data;
  const lastUpdatedTime = new Date(last_updated);
  const diffMinutes = (now - lastUpdatedTime.getTime()) / 1000 / 60;
  const isActuallyRunning = status === 'running' && diffMinutes <= 5;

  let translatedStatus = 'Desconhecido';
  if (isActuallyRunning) translatedStatus = 'em Execução';
  else if (status === 'running') translatedStatus = 'em Execução';
  else if (status === 'idle') translatedStatus = 'Ocioso';
  else if (status) translatedStatus = status;

  return (
    <article>
      <header>
        {isActuallyRunning ? (
          <span className="cg-pulse"></span>
        ) : null}
        <hgroup>
          <h2>
            Pipeline {translatedStatus}
            {source === 'ntfy-sse' && (
              <span> ● live</span>
            )}
          </h2>
          <small>
            Atualizado às {lastUpdatedTime.toLocaleTimeString()}
          </small>
        </hgroup>
      </header>

      <div>
        <div>
          <small>ZIPs Enviados</small>
          <strong>{zips_uploaded ?? '—'}</strong>
        </div>
        <div>
          <small>Tribunais Ativos</small>
          <strong>{active_tribunals ?? '—'}</strong>
        </div>
      </div>
    </article>
  );
}
