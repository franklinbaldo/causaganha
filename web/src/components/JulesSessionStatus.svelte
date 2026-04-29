<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchWithRetry } from '../lib/fetchData';

  let { apiKey = '' }: { apiKey?: string } = $props();

  interface Session {
    name: string; // The full name, typically includes ID
    title: string;
    state: string;
    createTime: string;
  }

  let sessions = $state<Session[]>([]);
  let loading = $state(false);
  let error = $state('');

  onMount(async () => {
    // If no API key is provided, we try to load it from localStorage for convenience during development
    if (!apiKey && typeof localStorage !== 'undefined') {
      apiKey = localStorage.getItem('JULES_API_KEY') || '';
    }

    if (!apiKey) {
      error = 'No Jules API Key provided. Please set JULES_API_KEY in your environment or local storage.';
      return;
    }

    fetchSessions();
  });

  async function fetchSessions() {
    loading = true;
    error = '';
    try {
      const response = await fetchWithRetry('https://jules.googleapis.com/v1alpha/sessions', {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        }
      }) as Response;

      if (!response.ok) {
        throw new Error(`Error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      sessions = data.sessions || [];
      // Keep only the last 5
      sessions = sessions.slice(0, 5);
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : 'Failed to fetch sessions';
    } finally {
      loading = false;
    }
  }

  function getStateColor(state: string) {
    switch (state) {
      case 'IN_PROGRESS': return 'badge-info';
      case 'COMPLETED': return 'badge-success';
      case 'FAILED': return 'badge-error';
      case 'AWAITING_USER_FEEDBACK': return 'badge-warning';
      default: return 'badge-ghost';
    }
  }

  function formatDate(isoString: string) {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString('pt-BR');
  }
</script>

<div class="card jules-card">
  <div class="card-body">
    <h3 class="card-title jules-header">
      Jules Sessions
      <button class="btn btn-sm btn-ghost" onclick={fetchSessions} disabled={loading || !apiKey}>
        <svg xmlns="http://www.w3.org/2000/svg" class="jules-refresh-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
    </h3>

    {#if error}
      <div class="jules-alert jules-alert-error">
        <svg xmlns="http://www.w3.org/2000/svg" class="jules-alert-icon" fill="none" viewBox="0 0 24 24"><path stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <span>{error}</span>
      </div>
    {:else if loading}
      <div class="jules-loading" aria-busy="true">
        <span class="jules-spinner"></span>
      </div>
    {:else if sessions.length === 0}
      <div class="jules-empty">
        No active sessions found.
      </div>
    {:else}
      <div class="jules-table-wrap">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>State</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {#each sessions as session}
              <tr>
                <td class="jules-id-cell">
                  {session.name ? session.name.split('/').pop() : 'Unknown'}
                </td>
                <td class="jules-title-cell" title={session.title}>{session.title || 'Untitled'}</td>
                <td>
                  <span class="badge badge-sm {getStateColor(session.state)}">
                    {session.state || 'UNKNOWN'}
                  </span>
                </td>
                <td class="jules-created-at">
                  {formatDate(session.createTime)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

<style>
  .jules-card {
    background: var(--color-base-100);
    border: 1px solid var(--color-base-300);
    box-shadow: var(--shadow-sm);
  }

  .jules-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
  }

  .jules-refresh-icon {
    width: 1rem;
    height: 1rem;
  }

  .jules-alert {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-sm);
    border-radius: var(--radius-box);
    font-size: var(--font-size-sm);
  }

  .jules-alert-error {
    background: color-mix(in srgb, var(--color-error) 10%, var(--color-base-100));
    color: var(--color-error-content, var(--color-base-content));
  }

  .jules-alert-icon {
    width: 1rem;
    height: 1rem;
    flex-shrink: 0;
  }

  .jules-loading {
    display: flex;
    justify-content: center;
    padding: var(--space-md) 0;
  }

  .jules-spinner {
    width: 1.25rem;
    height: 1.25rem;
    border: 2px solid var(--color-base-300);
    border-top-color: var(--color-primary);
    border-radius: 9999px;
    animation: jules-spin 0.8s linear infinite;
  }

  .jules-empty {
    padding: var(--space-md) 0;
    text-align: center;
    color: color-mix(in srgb, var(--color-base-content) 50%, transparent);
    font-size: var(--font-size-sm);
  }

  .jules-table-wrap {
    overflow-x: auto;
  }

  .jules-id-cell {
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
  }

  .jules-title-cell {
    max-width: 16rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .jules-created-at {
    white-space: nowrap;
    font-size: var(--font-size-xs);
    color: color-mix(in srgb, var(--color-base-content) 70%, transparent);
  }

  @keyframes jules-spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
