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

  let showDetails = $state(false);

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

<QueryProvider>
<div class="card"><div class="card-body">
  <div class="status-layout">
    <!-- Left: status & stats -->
    <div class="status-left">
      <div class="status-indicator" role="status" aria-live="polite">
        {#if stats}
          {#if isSuccess}
            <div class="icon-circle icon-circle--success">
              <svg class="icon icon--success" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
          {:else}
            <div class="icon-circle icon-circle--error">
              <svg class="icon icon--error" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
          {/if}
        {:else}
          <div></div>
        {/if}
        <div class="status-text">
          <div class="status-title">
            {#if stats}
              {isSuccess ? 'Pipeline operacional' : 'Falha no pipeline'}
            {:else}
              Carregando...
            {/if}
          </div>
          {#if stats?.timestamp}
            <small class="status-timestamp">
              Última execução: {new Date(stats.timestamp).toLocaleString('pt-BR')}
            </small>
          {/if}
          <span class="status-subtitle">
            {#if stats}
              {isSuccess ? 'Sistema operacional' : 'Falha detectada no sistema'}
            {:else}
              Carregando status do sistema
            {/if}
          </span>
        </div>
      </div>

      <!-- Stat pills -->
      <div class="stat-pills">
        {#if health != null}
          <div class="stat-pill">
            <svg class="pill-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
            </svg>
            <span>Health:</span>
            <span
              class={health >= 70 ? 'text-success' : health >= 40 ? 'text-warning' : 'text-error'}
              aria-label={`Saúde: ${health}% — ${health >= 70 ? 'Saudável' : health >= 40 ? 'Atenção' : 'Crítico'}`}
            >
              {health}% <span class="health-label">{health >= 70 ? 'Saudável' : health >= 40 ? 'Atenção' : 'Crítico'}</span>
            </span>
          </div>
        {/if}
        {#if filesToday != null}
          <div class="stat-pill">
            <span>{isDataStale ? dataDate : 'Hoje'}:</span>
            <span class={isDataStale ? 'text-warning' : ''}>{filesToday}/91</span>
            {#if isDataStale}
              <span class="text-warning" title="A coleta de dados parece travada — sem novos dados desde esta data">defasado</span>
            {/if}
          </div>
        {/if}
        {#if stats?.duration_seconds != null}
          <div class="stat-pill">
            <svg class="pill-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>{stats.duration_seconds}s</span>
          </div>
        {/if}
      </div>
    </div>

    <!-- Right: countdown & actions -->
    <div class="status-right">
      {#if stats?.timestamp}
        <div class="countdown-block">
          <small class="countdown-label">Próxima execução</small>
          <div class="countdown-value">{countdown}</div>
        </div>
      {/if}

      {#if stats?.steps}
        <button
          class="toggle-btn"
          onclick={() => showDetails = !showDetails}
          aria-expanded={showDetails}
          aria-label="Alternar detalhes da execução">
          {#if showDetails}
            <svg class="toggle-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m18 15-6-6-6 6"/>
            </svg>
          {:else}
            <svg class="toggle-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m6 9 6 6 6-6"/>
            </svg>
          {/if}
        </button>
      {/if}
    </div>
  </div>

  <!-- Expandable details -->
  {#if stats?.steps && showDetails}
    <div class="details-section">
      <div class="details-inner">
        <h3 class="details-heading">Etapas do pipeline</h3>
        <div class="steps-list">
          {#each Object.entries(stats.steps) as [stepName, stepData]}
            {@const isOk = (stepData.success !== 0 && stepData.failed === 0) || stepData.success === true}
            <div class="step-item">
              <div class="step-header">
                <span class="step-name">
                  {stepName.replace(/_/g, ' ')}
                </span>
                <span class="badge {isOk ? 'badge--success' : 'badge--error'}">
                  {#if isOk}
                    <svg class="badge-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                  {:else}
                    <svg class="badge-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                  {/if}
                  <span>{isOk ? 'OK' : 'Falha'}</span>
                </span>
              </div>
              <div class="step-details">
                {#each Object.entries(stepData) as [k, v]}
                  {#if k !== 'success'}
                    <div class="step-detail-row">
                      <span class="step-detail-key">{k.replace(/_/g, ' ')}</span>
                      <span class="step-detail-value">{v}</span>
                    </div>
                  {/if}
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <!-- IA Task Status -->
  {#if cacheToday?.ia_tasks?.pending_count > 0}
    <div class="ia-tasks-notice">
      <svg class="pill-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
      </svg>
      <span>{cacheToday.ia_tasks.pending_count} tarefa(s) de processamento pendente(s) no Internet Archive</span>
    </div>
  {/if}

  <!-- Footer -->
  <footer class="status-footer">
    <small class="footer-text">Pipeline executa a cada {PIPELINE_INTERVAL_MINUTES} minutos via GitHub Actions</small>
    <a
      class="footer-link"
      href="https://github.com/franklinbaldo/causaganha/actions" target="_blank"
      rel="noopener noreferrer">
      Ver Actions
      <svg class="footer-link-icon" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      </svg>
    </a>
  </footer>
</div></div>
</QueryProvider>

<style>

  .status-layout {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    flex-wrap: wrap;
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
    border-radius: var(--radius-full);
    flex-shrink: 0;
  }

  .icon-circle--success {
    background: color-mix(in srgb, var(--color-success) 15%, var(--color-base-100));
  }

  .icon-circle--error {
    background: color-mix(in srgb, var(--color-error) 15%, var(--color-base-100));
  }

  .icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  .icon--success {
    color: var(--color-success);
  }

  .icon--error {
    color: var(--color-error);
  }

  .status-text {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .status-title {
    font-weight: 600;
    font-size: var(--font-size-base);
  }

  .status-timestamp {
    font-size: var(--font-size-xs);
    opacity: 0.6;
  }

  .status-subtitle {
    font-size: var(--font-size-sm);
    opacity: 0.6;
  }

  .stat-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
  }

  .stat-pill {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    font-size: var(--font-size-sm);
  }

  .pill-icon {
    width: 1rem;
    height: 1rem;
    opacity: 0.6;
  }

  .health-label {
    font-size: var(--font-size-xs);
    font-weight: 600;
    opacity: 0.8;
  }

  .text-success {
    color: var(--color-success);
  }

  .text-error {
    color: var(--color-error);
  }

  .text-warning {
    color: var(--color-warning);
  }

  .status-right {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .countdown-block {
    text-align: center;
  }

  .countdown-label {
    font-size: var(--font-size-xs);
    opacity: 0.6;
  }

  .countdown-value {
    color: var(--color-accent);
    font-size: var(--font-size-lg);
    font-weight: 700;
    font-family: var(--font-mono);
  }

  .toggle-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.375rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-btn);
    background: transparent;
    cursor: pointer;
    transition: all var(--transition-base);
    color: var(--color-base-content);
  }

  .toggle-btn:hover {
    background: var(--color-base-200);
  }

  .toggle-icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  .details-section {
    margin-top: 1.5rem;
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.5rem;
  }

  .details-inner {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .details-heading {
    font-size: var(--font-size-md);
    font-weight: 600;
    margin: 0;
  }

  .steps-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .step-item {
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-sm);
    padding: 0.75rem;
  }

  .step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .step-name {
    font-weight: 500;
    text-transform: capitalize;
    font-size: var(--font-size-sm);
  }

  .badge--success {
    background: color-mix(in srgb, var(--color-success) 15%, var(--color-base-100));
    color: var(--color-success);
  }

  .badge--error {
    background: color-mix(in srgb, var(--color-error) 15%, var(--color-base-100));
    color: var(--color-error);
  }

  .badge-icon {
    width: 0.875rem;
    height: 0.875rem;
  }

  .step-details {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .step-detail-row {
    display: flex;
    justify-content: space-between;
    font-size: var(--font-size-xs);
  }

  .step-detail-key {
    opacity: 0.6;
    text-transform: capitalize;
  }

  .step-detail-value {
    font-weight: 500;
  }

  .ia-tasks-notice {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    font-size: var(--font-size-sm);
    color: var(--color-warning);
    padding: 0.75rem;
    background: color-mix(in srgb, var(--color-warning) 10%, var(--color-base-100));
    border: 1px solid color-mix(in srgb, var(--color-warning) 30%, transparent);
    border-radius: var(--radius-sm);
  }

  .status-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-base-300);
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .footer-text {
    opacity: 0.5;
    font-size: var(--font-size-xs);
  }

  .footer-link {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: var(--font-size-xs);
    color: var(--color-primary);
    text-decoration: none;
  }

  .footer-link:hover {
    text-decoration: underline;
  }

  .footer-link-icon {
    width: 0.875rem;
    height: 0.875rem;
  }
</style>
