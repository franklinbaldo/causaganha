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

  function stateTone(state: string): string {
    switch (state) {
      case 'IN_PROGRESS': return 'info';
      case 'COMPLETED': return 'success';
      case 'FAILED': return 'error';
      case 'AWAITING_USER_FEEDBACK': return 'warning';
      default: return '';
    }
  }

  function formatDate(isoString: string) {
    if (!isoString) return 'N/A';
    return new Date(isoString).toLocaleString('pt-BR');
  }
</script>

<article>
  <header class="jules-header">
    <h3>Jules Sessions</h3>
    <button type="button" class="outline secondary" onclick={fetchSessions} disabled={loading || !apiKey} aria-label="Atualizar">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    </button>
  </header>

  {#if error}
    <aside role="alert" class="error-alert">{error}</aside>
  {:else if loading}
    <p aria-busy="true">Carregando sessões...</p>
  {:else if sessions.length === 0}
    <p class="empty">No active sessions found.</p>
  {:else}
    <div class="table-wrap">
      <table>
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
              <td><kbd class="id-cell">{session.name ? session.name.split('/').pop() : 'Unknown'}</kbd></td>
              <td class="title-cell" title={session.title}>{session.title || 'Untitled'}</td>
              <td>
                <mark data-tone={stateTone(session.state)}>{session.state || 'UNKNOWN'}</mark>
              </td>
              <td><small>{formatDate(session.createTime)}</small></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</article>
