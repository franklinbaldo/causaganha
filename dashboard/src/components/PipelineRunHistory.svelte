<script lang="ts">
  import { onMount } from 'svelte';

  interface WorkflowRun {
    id: number;
    status: string;
    conclusion: string | null;
    created_at: string;
    updated_at: string;
    html_url: string;
  }

  interface WorkflowRunsResponse {
    workflow_runs: WorkflowRun[];
  }

  let runs = $state<WorkflowRun[]>([]);
  let loading = $state<boolean>(true);
  let error = $state<string | null>(null);

  const calculateDuration = (createdAt: string, updatedAt: string): number => {
    const start = new Date(createdAt);
    const end = new Date(updatedAt);
    const diffMs = end.getTime() - start.getTime();
    const diffMins = Math.round(diffMs / 60000);
    return diffMins;
  };

  onMount(async () => {
    try {
      const response = await fetch('https://api.github.com/repos/franklinbaldo/causaganha/actions/workflows/collect-zips.yml/runs?per_page=7');
      if (!response.ok) {
        throw new Error(`Failed to fetch runs: ${response.status} ${response.statusText}`);
      }
      const data: WorkflowRunsResponse = await response.json();
      runs = data.workflow_runs || [];
    } catch (err: unknown) {
      error = err instanceof Error ? err.message : String(err);
    } finally {
      loading = false;
    }
  });
</script>

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body">
    <h3>Pipeline Run History (Collect ZIPs)</h3>

    {#if loading}
      <div>Loading run history...</div>
    {/if}

    {#if error}
      <div>Error: {error}</div>
    {/if}

    {#if !loading && !error}
      <div class="table-responsive">
        <table class="table table-zebra table-sm">
          <thead>
            <tr>
              <th>Run Date</th>
              <th>Duration (min)</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {#each runs as run (run.id)}
              <tr>
                <td>
                  <a href={run.html_url} target="_blank" rel="noopener noreferrer">
                    {new Date(run.created_at).toLocaleString()}
                  </a>
                </td>
                <td>
                  {calculateDuration(run.created_at, run.updated_at)}
                </td>
                <td>
                  {#if run.status !== 'completed'}
                    <span title="In Progress">⏳</span>
                  {:else if run.conclusion === 'success'}
                    <span title="Success">✅</span>
                  {:else}
                    <span title="Failure">❌</span>
                  {/if}
                </td>
              </tr>
            {/each}
            {#if runs.length === 0}
              <tr>
                <td colspan="3">No runs found.</td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
