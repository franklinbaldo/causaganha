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
  <header role="status" aria-live="polite">
    {#if stats}
      <span data-tone={isSuccess ? 'success' : 'error'} aria-hidden="true">
        {#if isSuccess}
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        {:else}
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        {/if}
      </span>
    {/if}
    <hgroup>
      <h2>
        {#if stats}
          {isSuccess ? 'Pipeline operacional' : 'Falha no pipeline'}
        {:else}
          Carregando...
        {/if}
      </h2>
      <p>
        {#if stats?.timestamp}
          Última execução: {new Date(stats.timestamp).toLocaleString('pt-BR')}
        {:else if stats}
          {isSuccess ? 'Sistema operacional' : 'Falha detectada no sistema'}
        {:else}
          Carregando status do sistema
        {/if}
      </p>
    </hgroup>
    {#if stats?.timestamp}
      <div class="system-status__next-run">
        <small>Próxima execução</small>
        <data class="system-status__countdown" value={countdown}>{countdown}</data>
      </div>
    {/if}
  </header>

  <dl class="auto-grid-sm">
    {#if health != null}
      <div>
        <dt>
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
            <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
          </svg>
          Health
        </dt>
        <dd>
          <strong data-tone={health >= 70 ? 'success' : health >= 40 ? 'warning' : 'error'}
            aria-label={`Saúde: ${health}% — ${health >= 70 ? 'Saudável' : health >= 40 ? 'Atenção' : 'Crítico'}`}>
            {health}% {health >= 70 ? 'Saudável' : health >= 40 ? 'Atenção' : 'Crítico'}
          </strong>
        </dd>
      </div>
    {/if}
    {#if filesToday != null}
      <div>
        <dt>{isDataStale ? dataDate : 'Hoje'}</dt>
        <dd>
          <strong data-tone={isDataStale ? 'warning' : undefined}>{filesToday}/91</strong>
          {#if isDataStale}
            <small data-tone="warning" title="A coleta de dados parece travada — sem novos dados desde esta data">defasado</small>
          {/if}
        </dd>
      </div>
    {/if}
    {#if stats?.duration_seconds != null}
      <div>
        <dt>
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="16" height="16">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
          Duração
        </dt>
        <dd>{stats.duration_seconds}s</dd>
      </div>
    {/if}
  </dl>

  <!-- Expandable pipeline steps using native <details> -->
  {#if stats?.steps}
    <details>
      <summary>Etapas do pipeline</summary>
      <div class="auto-grid">
        {#each Object.entries(stats.steps) as [stepName, stepData]}
          {@const isOk = (stepData.success !== 0 && stepData.failed === 0) || stepData.success === true}
          <article>
            <header>
              <span>{stepName.replace(/_/g, ' ')}</span>
              <mark data-tone={isOk ? 'success' : 'error'}>{isOk ? 'OK' : 'Erro'}</mark>
            </header>
            <dl>
              {#each Object.entries(stepData) as [k, v]}
                {#if k !== 'success'}
                  <div>
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
    <aside role="alert" class="alert" data-level="info">
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

<style>
  .system-status__next-run {
    display: grid;
    gap: var(--space-1);
  }

  .system-status__countdown {
    display: inline-flex;
    width: fit-content;
    padding: var(--space-1) var(--space-2);
    border: 1px solid var(--color-border-muted);
    border-radius: var(--radius-pill);
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    font-variant-numeric: tabular-nums;
    background: var(--color-surface-elevated);
  }
</style>
