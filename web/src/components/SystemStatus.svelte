<script lang="ts">
  import QueryProvider from './QueryProvider.svelte';
  import { useDashboardWithPolling } from '../lib/useDashboard.svelte';

  const PIPELINE_INTERVAL_MINUTES = 20;

  interface SystemStatusProps {
    initialStats: any;
    initialCacheToday: any;
  }

  let { initialStats, initialCacheToday }: SystemStatusProps = $props();

  const dashboard = useDashboardWithPolling();

  // showDetails is now managed by native <details> open attribute

  // Use refreshed data if available, fall back to initial props
  let stats = $derived(dashboard.data?.stats ?? initialStats);
  let cacheToday = $derived(dashboard.data?.cacheData?.today ?? initialCacheToday);

  let isSuccess = $derived(stats?.status === 'success');
  let health = $derived(cacheToday?.health);
  let filesToday = $derived(cacheToday?.files_today);
  let dataDate = $derived(cacheToday?.date);

  const now = Date.now();
  let isDataStale = $derived.by(() => {
    if (!dataDate) return false;
    const today = new Date(now).toISOString().slice(0, 10);
    const yesterday = new Date(now - 86400000).toISOString().slice(0, 10);
    return dataDate !== today && dataDate !== yesterday;
  });

  // Next run countdown (replaces useNextRunCountdown hook)
  let countdown = $state('--:--');

  $effect(() => {
    const lastRunTimestamp = stats?.timestamp;
    if (!lastRunTimestamp) {
      countdown = '--:--';
      return;
    }

    const update = () => {
      const lastRun = new Date(lastRunTimestamp).getTime();
      const nextRun = lastRun + PIPELINE_INTERVAL_MINUTES * 60 * 1000;
      const remaining = Math.max(0, nextRun - Date.now());
      const mins = Math.floor(remaining / 60000);
      const secs = Math.floor((remaining % 60000) / 1000);
      countdown = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    };

    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  });
</script>

<article>
  <div class="status-layout" role="status" aria-live="polite">
    <!-- Left: status & stats -->
    <div class="status-left">
      <div class="status-indicator">
        {#if stats}
          <div class="icon-circle" data-tone={isSuccess ? 'success' : 'error'}>
            {#if isSuccess}
              <svg class="icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            {:else}
              <svg class="icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            {/if}
          </div>
        {/if}
        <div class="status-text">
          <strong>
            {#if stats}
              {isSuccess ? 'Pipeline operacional' : 'Falha no pipeline'}
            {:else}
              Carregando...
            {/if}
          </strong>
          {#if stats?.timestamp}
            <small>Última execução: {new Date(stats.timestamp).toLocaleString('pt-BR')}</small>
          {/if}
          <small>
            {#if stats}
              {isSuccess ? 'Sistema operacional' : 'Falha detectada no sistema'}
            {:else}
              Carregando status do sistema
            {/if}
          </small>
        </div>
      </div>

      <div class="stat-pills">
        {#if health != null}
          <span class="stat-pill">
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
            </svg>
            Health:
            <strong data-tone={health >= 70 ? 'success' : health >= 40 ? 'warning' : 'error'}
              aria-label={`Saúde: ${health}% — ${health >= 70 ? 'Saudável' : health >= 40 ? 'Atenção' : 'Crítico'}`}>
              {health}% {health >= 70 ? 'Saudável' : health >= 40 ? 'Atenção' : 'Crítico'}
            </strong>
          </span>
        {/if}
        {#if filesToday != null}
          <span class="stat-pill">
            {isDataStale ? dataDate : 'Hoje'}:
            <strong data-tone={isDataStale ? 'warning' : undefined}>{filesToday}/91</strong>
            {#if isDataStale}
              <small data-tone="warning" title="A coleta parece estar parada — sem novos dados desde esta data">desatualizado</small>
            {/if}
          </span>
        {/if}
        {#if stats?.duration_seconds != null}
          <span class="stat-pill">
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            {stats.duration_seconds}s
          </span>
        {/if}
      </div>
    </div>

    <!-- Right: countdown -->
    {#if stats?.timestamp}
      <div class="countdown-block">
        <small>Próxima execução</small>
        <kbd class="countdown-value">{countdown}</kbd>
      </div>
    {/if}
  </div>

  <!-- Expandable pipeline steps using native <details> -->
  {#if stats?.steps}
    <details class="steps-details">
      <summary>Etapas do pipeline</summary>
      <div class="steps-list">
        {#each Object.entries(stats.steps) as [stepName, stepData]}
          {@const isOk = (stepData.success !== 0 && stepData.failed === 0) || stepData.success === true}
          <article class="step-item">
            <header>
              <span>{stepName.replace(/_/g, ' ')}</span>
              <mark data-tone={isOk ? 'success' : 'error'}>{isOk ? 'OK' : 'Erro'}</mark>
            </header>
            <dl>
              {#each Object.entries(stepData) as [k, v]}
                {#if k !== 'success'}
                  <div class="dl-row">
                    <dt>{k.replace(/_/g, ' ')}</dt>
                    <dd>{v}</dd>
                  </div>
                {/if}
              {/each}
            </dl>
          </article>
        {/each}
      </div>
    </details>
  {/if}

  <!-- IA Task Status -->
  {#if cacheToday?.ia_tasks?.pending_count > 0}
    <aside role="alert" class="ia-alert">
      <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
      </svg>
      {cacheToday.ia_tasks.pending_count} tarefa(s) de processamento pendente(s) no Internet Archive
    </aside>
  {/if}

  <footer>
    <small>Pipeline executa a cada {PIPELINE_INTERVAL_MINUTES} minutos via GitHub Actions</small>
    <a href="https://github.com/franklinbaldo/causaganha/actions" target="_blank" rel="noopener noreferrer">
      Ver Actions
      <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14">
        <path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      </svg>
    </a>
  </footer>
</article>
</QueryProvider>

<style>
  .status-layout {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
  }

  .status-left {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .icon-circle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .icon-circle[data-tone='success'] {
    background: color-mix(in srgb, var(--color-success) 15%, transparent);
    color: var(--color-success);
  }
  .icon-circle[data-tone='error'] {
    background: color-mix(in srgb, var(--color-error) 15%, transparent);
    color: var(--color-error);
  }

  .icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  .status-text {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }

  .stat-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
  }

  .stat-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    font-size: var(--font-size-sm);
  }

  [data-tone='success'] { color: var(--color-success); }
  [data-tone='warning'] { color: var(--color-warning); }
  [data-tone='error']   { color: var(--color-error); }

  .countdown-block {
    text-align: center;
  }

  .countdown-value {
    color: var(--color-accent);
    font-size: var(--font-size-lg);
    font-weight: 700;
  }

  .steps-details {
    margin-top: 1rem;
  }

  .steps-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 0.75rem;
  }

  .step-item {
    margin-bottom: 0;
  }

  .step-item header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: none;
    padding: 0;
    margin-bottom: 0.5rem;
    text-transform: capitalize;
  }

  dl { margin: 0; }

  .dl-row {
    display: flex;
    justify-content: space-between;
    font-size: var(--font-size-xs);
    gap: 1rem;
  }

  .dl-row dt {
    opacity: 0.6;
    text-transform: capitalize;
  }

  .dl-row dd {
    font-weight: 500;
    margin: 0;
  }

  .ia-alert {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    padding: 0.75rem;
    font-size: var(--font-size-sm);
    color: var(--color-warning);
    background: color-mix(in srgb, var(--color-warning) 10%, transparent);
    border: 1px solid color-mix(in srgb, var(--color-warning) 30%, transparent);
    border-radius: var(--pico-border-radius);
  }

  footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    background: none;
  }

  footer small {
    opacity: 0.5;
  }

  footer a {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--font-size-xs);
  }
</style>
