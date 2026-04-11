<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchWithRetry } from '../lib/fetchData';

  export let apiKey: string = '';

  interface Session {
    name: string; // The full name, typically includes ID
    title: string;
    state: string;
    createTime: string;
  }

  let sessions: Session[] = [];
  let loading = false;
  let error = '';

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
    } catch (err: any) {
      error = err.message || 'Failed to fetch sessions';
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

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body">
    <h3 class="card-title mb-4 flex justify-between items-center">
      Jules Sessions
      <button class="btn btn-sm btn-ghost" on:click={fetchSessions} disabled={loading || !apiKey}>
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
    </h3>

    {#if error}
      <div class="alert alert-error text-sm">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <span>{error}</span>
      </div>
    {:else if loading}
      <div class="flex justify-center py-4" aria-busy="true">
        <span class="loading loading-spinner loading-md text-primary"></span>
      </div>
    {:else if sessions.length === 0}
      <div class="text-center py-4 text-base-content/50 text-sm">
        No active sessions found.
      </div>
    {:else}
      <div class="overflow-x-auto">
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
                <td class="font-mono text-xs">
                  <a href="#" class="link link-hover link-primary" title="Open in console">
                    <!-- Extracting ID if it's in the format 'sessions/ID' -->
                    {session.name ? session.name.split('/').pop() : 'Unknown'}
                  </a>
                </td>
                <td class="whitespace-nowrap max-w-xs truncate" title={session.title}>{session.title || 'Untitled'}</td>
                <td>
                  <span class="badge badge-sm {getStateColor(session.state)}">
                    {session.state || 'UNKNOWN'}
                  </span>
                </td>
                <td class="text-xs text-base-content/70 whitespace-nowrap">
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
