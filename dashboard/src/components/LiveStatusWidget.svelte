<script lang="ts">
  import { onMount } from 'svelte';

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

  let data = $state<LiveStatusData | null>(null);
  let error = $state<boolean>(false);
  let source = $state<'loading' | 'ntfy-sse' | 'polling'>('loading');
  let now = $state<number>(Date.now());

  const lastUpdatedTime = $derived(data ? new Date(data.last_updated) : null);
  const diffMinutes = $derived(lastUpdatedTime ? (now - lastUpdatedTime.getTime()) / 1000 / 60 : 0);
  const isActuallyRunning = $derived(data?.status === 'running' && diffMinutes <= 5);

  const translatedStatus = $derived.by(() => {
    if (!data) return 'Desconhecido';
    if (isActuallyRunning) return 'em Execução';
    if (data.status === 'running') return 'em Execução';
    if (data.status === 'idle') return 'Ocioso';
    if (data.status) return data.status;
    return 'Desconhecido';
  });

  onMount(() => {
    let isMounted = true;
    let es: EventSource | null = null;
    let fallbackInterval: ReturnType<typeof setInterval> | null = null;

    const timer = setInterval(() => { now = Date.now(); }, 60000);

    const applyMessage = (msgStr: string) => {
      try {
        const parsed: LiveStatusData = JSON.parse(msgStr);
        if (isMounted) {
          data = parsed;
          error = false;
        }
      } catch { /* ignore parse errors */ }
    };

    // Try ntfy SSE first (real-time push)
    const startSSE = () => {
      try {
        es = new EventSource(NTFY_SSE_URL);
        es.onopen = () => {
          if (isMounted) source = 'ntfy-sse';
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
      source = 'polling';

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
              data = json;
              error = false;
            }
          }
        } catch {
          if (isMounted) error = true;
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
      clearInterval(timer);
      if (es) es.close();
      if (fallbackInterval) clearInterval(fallbackInterval);
    };
  });
</script>

{#if error}
  <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
    <span>Status ao vivo indisponível.</span>
  </div></div>
{:else if !data}
  <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
    <span aria-busy="true">Carregando status do pipeline...</span>
  </div></div>
{:else}
  <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
    <header>
      {#if isActuallyRunning}
        <span class="cg-pulse"></span>
      {/if}
      <hgroup>
        <h2>
          Pipeline {translatedStatus}
          {#if source === 'ntfy-sse'}
            <span> ● live</span>
          {/if}
        </h2>
        <small>
          Atualizado às {lastUpdatedTime!.toLocaleTimeString()}
        </small>
      </hgroup>
    </header>

    <div>
      <div>
        <small>ZIPs Enviados</small>
        <strong>{data.zips_uploaded ?? '—'}</strong>
      </div>
      <div>
        <small>Tribunais Ativos</small>
        <strong>{data.active_tribunals ?? '—'}</strong>
      </div>
    </div>
  </div></div>
{/if}
