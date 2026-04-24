<script lang="ts">
  interface BackfillTribunal {
    tribunal: string;
    state: string;
    genesis_date: string;
    cursor_date: string | null;
    completion_pct: number;
  }

  interface BackfillData {
    tribunals?: BackfillTribunal[];
    updated_at?: string;
  }

  let { data = null }: { data: BackfillData | null } = $props();

  let tribunals = $derived(data?.tribunals ?? []);
  let updatedAt = $derived(data?.updated_at ? new Date(data.updated_at).toLocaleString('pt-BR') : 'N/A');
</script>

<div class="card backfill-card">
  <div class="card-body backfill-card-body">
    <div class="backfill-header">
      <h2 class="card-title backfill-title">Detalhes de Backfill por Tribunal</h2>
      <span class="backfill-updated-at">Última verificação: {updatedAt}</span>
    </div>

    {#if tribunals.length === 0}
      <div class="backfill-empty">Nenhum dado de backfill disponível.</div>
    {:else}
      <div class="table-responsive">
        <table class="table backfill-table">
          <thead>
            <tr>
              <th>Tribunal</th>
              <th>Estado</th>
              <th>Data Gênesis</th>
              <th>Cursor Atual</th>
              <th>Progresso</th>
            </tr>
          </thead>
          <tbody>
            {#each tribunals as t}
              <tr>
                <td class="backfill-tribunal">{t.tribunal}</td>
                <td>
                  {#if t.state === 'Active'}
                    <span class="badge badge-success badge-sm">Ativo</span>
                  {:else if t.state === 'Paused'}
                    <span class="badge badge-warning badge-sm">Pausado</span>
                  {:else if t.state === 'Stopped'}
                    <span class="badge badge-error badge-sm">Parado</span>
                  {:else}
                    <span class="badge badge-ghost badge-sm">{t.state}</span>
                  {/if}
                </td>
                <td class="backfill-meta">{t.genesis_date}</td>
                <td class="backfill-mono">{t.cursor_date || 'N/A'}</td>
                <td class="backfill-progress-cell">
                  <div class="backfill-progress">
                    <progress class="progress backfill-progress-bar" value={t.completion_pct} max="100"></progress>
                    <span class="backfill-progress-value">{t.completion_pct}%</span>
                  </div>
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
  .backfill-card {
    background: var(--color-base-100);
    border: 1px solid var(--color-base-300);
    box-shadow: var(--shadow-sm);
  }

  .backfill-card-body {
    padding: var(--space-lg);
  }

  .backfill-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-md);
    flex-wrap: wrap;
  }

  .backfill-title {
    font-size: var(--font-size-xl);
  }

  .backfill-updated-at {
    font-size: var(--font-size-xs);
    opacity: 0.7;
  }

  .backfill-empty {
    padding: var(--space-md);
    border-radius: var(--radius-box);
    background: color-mix(in srgb, var(--color-info) 10%, var(--color-base-100));
    color: var(--color-info-content, var(--color-base-content));
  }

  .backfill-table {
    width: 100%;
  }

  .backfill-table tbody tr:nth-child(even) {
    background: var(--color-base-200);
  }

  .backfill-tribunal {
    font-weight: 700;
  }

  .backfill-meta {
    font-size: var(--font-size-xs);
    opacity: 0.8;
  }

  .backfill-mono {
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
  }

  .backfill-progress-cell {
    width: 33%;
    min-width: 150px;
  }

  .backfill-progress {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }

  .backfill-progress-bar {
    flex: 1;
  }

  .backfill-progress-value {
    width: 2.5rem;
    text-align: right;
    font-size: var(--font-size-xs);
    font-weight: 500;
  }
</style>
