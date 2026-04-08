<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createDataRefresh } from '../lib/dataRefreshStore';

  const PIPELINE_INTERVAL_MINUTES = 20;

  interface SystemStatusProps {
    initialStats: any;
    initialCacheToday: any;
  }

  let { initialStats, initialCacheToday }: SystemStatusProps = $props();

  const store = createDataRefresh(null, null);
  onMount(() => store.start());
  onDestroy(() => store.stop());

  let showDetails = $state(false);

  // Use refreshed data if available, fall back to initial props
  let stats = $derived($store.data?.stats ?? initialStats);
  let cacheToday = $derived($store.data?.cacheData?.today ?? initialCacheToday);

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

<div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
  <div>
    <!-- Left: status & stats -->
    <div>
      <div role="status" aria-live="polite">
        {#if stats}
          {#if isSuccess}
            <div class="bg-success-muted">
              <svg class="text-success" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
            </div>
          {:else}
            <div class="bg-danger-muted">
              <svg class="text-error" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
            </div>
          {/if}
        {:else}
          <div></div>
        {/if}
        <div>
          <div>
            {#if stats}
              {isSuccess ? 'Pipeline Operational' : 'Pipeline Issue'}
            {:else}
              Loading...
            {/if}
          </div>
          {#if stats?.timestamp}
            <small>
              Last run: {new Date(stats.timestamp).toLocaleString()}
            </small>
          {/if}
          <span>
            {#if stats}
              {isSuccess ? 'System operational' : 'System fault detected'}
            {:else}
              Loading system status
            {/if}
          </span>
        </div>
      </div>

      <!-- Stat pills -->
      <div>
        {#if health != null}
          <div>
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"/>
            </svg>
            <span>Health:</span>
            <span class={health >= 70 ? 'text-success' : 'text-error'}>
              {health}%
            </span>
          </div>
        {/if}
        {#if filesToday != null}
          <div>
            <span>{isDataStale ? dataDate : 'Today'}:</span>
            <span class={isDataStale ? 'text-warning' : ''}>{filesToday}/91</span>
            {#if isDataStale}
              <span class="text-warning" title="Data collection appears stalled — no new data since this date">stale</span>
            {/if}
          </div>
        {/if}
        {#if stats?.duration_seconds != null}
          <div>
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>{stats.duration_seconds}s</span>
          </div>
        {/if}
      </div>
    </div>

    <!-- Right: countdown & actions -->
    <div>
      {#if stats?.timestamp}
        <div>
          <small>Next run</small>
          <div class="text-accent">{countdown}</div>
        </div>
      {/if}

      {#if stats?.steps}
        <button
          onclick={() => showDetails = !showDetails}
          aria-expanded={showDetails}
          aria-label="Toggle run details">
          {#if showDetails}
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m18 15-6-6-6 6"/>
            </svg>
          {:else}
            <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="m6 9 6 6 6-6"/>
            </svg>
          {/if}
        </button>
      {/if}
    </div>
  </div>

  <!-- Expandable details -->
  {#if stats?.steps && showDetails}
    <div>
      <div>
        <h3>Pipeline Steps</h3>
        <div>
          {#each Object.entries(stats.steps) as [stepName, stepData]}
            {@const isOk = (stepData.success !== 0 && stepData.failed === 0) || stepData.success === true}
            <div>
              <div>
                <span>
                  {stepName.replace(/_/g, ' ')}
                </span>
                <span class="badge {isOk ? 'badge-success' : 'badge-error'}">
                  {#if isOk}
                    <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                  {:else}
                    <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                    </svg>
                  {/if}
                  <span>{isOk ? 'OK' : 'Issue'}</span>
                </span>
              </div>
              <div>
                {#each Object.entries(stepData) as [k, v]}
                  {#if k !== 'success'}
                    <div>
                      <span>{k.replace(/_/g, ' ')}</span>
                      <span>{v}</span>
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
    <div>
      <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
      </svg>
      <span>{cacheToday.ia_tasks.pending_count} tarefa(s) de processamento pendente(s) no Internet Archive</span>
    </div>
  {/if}

  <!-- Footer -->
  <footer>
    <small>Pipeline runs every {PIPELINE_INTERVAL_MINUTES} minutes via GitHub Actions</small>
    <a
      href="https://github.com/franklinbaldo/causaganha/actions" target="_blank"
      rel="noopener noreferrer">
      View Actions
      <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
      </svg>
    </a>
  </footer>
</div></div>
