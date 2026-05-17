<script lang="ts">
  import { onMount } from 'svelte';
  import AlertBanner from './AlertBanner.svelte';
  import EmptyState from './EmptyState.svelte';

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

<div class="card">
  <div class="card-body">
    <h3>Histórico de Execuções do Pipeline (Collect ZIPs)</h3>

    {#if loading}
      <div>Carregando histórico de execuções...</div>
    {:else if error}
      <AlertBanner level="error" title="Erro ao carregar histórico" message={error} />
    {:else if runs.length === 0}
      <EmptyState title="Nenhuma execução encontrada" message="Não foram encontradas execuções recentes do pipeline." />
    {:else}
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th scope="col">Data da execução</th>
              <th scope="col">Duração (min)</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {#each runs as run (run.id)}
              <tr>
                <td>
                  <a href={run.html_url} target="_blank" rel="noopener noreferrer">
                    {new Date(run.created_at).toLocaleString('pt-BR')}
                  </a>
                </td>
                <td>
                  {calculateDuration(run.created_at, run.updated_at)}
                </td>
                <td>
                  {#if run.status !== 'completed'}
                    <span title="Em andamento" aria-label="Em andamento">⏳</span>
                  {:else if run.conclusion === 'success'}
                    <span title="Sucesso" aria-label="Sucesso">✅</span>
                  {:else}
                    <a href={run.html_url} target="_blank" rel="noopener noreferrer" title="Ver logs da falha" aria-label="Ver logs da falha">❌</a>
                  {/if}
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
  .table-responsive {
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
  }

  .data-table th,
  .data-table td {
    padding: 0.375rem 0.5rem;
    text-align: left;
    font-size: var(--font-size-sm);
  }

  .data-table tbody tr:nth-child(even) {
    background: var(--color-base-200);
  }
</style>
