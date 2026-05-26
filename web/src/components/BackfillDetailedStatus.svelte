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

<article>
  <header>
    <h2>Detalhes de Backfill por Tribunal</h2>
    <small>Última verificação: {updatedAt}</small>
  </header>

  {#if tribunals.length === 0}
    <p>Nenhum dado de backfill disponível.</p>
  {:else}
    <div class="table-wrap">
      <table>
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
              <td><strong>{t.tribunal}</strong></td>
              <td>
                {#if t.state === 'Active'}
                  <mark data-tone="success">Ativo</mark>
                {:else if t.state === 'Paused'}
                  <mark data-tone="warning">Pausado</mark>
                {:else if t.state === 'Stopped'}
                  <mark data-tone="error">Parado</mark>
                {:else}
                  <mark>{t.state}</mark>
                {/if}
              </td>
              <td><small>{t.genesis_date}</small></td>
              <td><kbd>{t.cursor_date || 'N/A'}</kbd></td>
              <td class="progress-cell">
                <progress value={t.completion_pct} max="100" aria-label="{t.tribunal}: {t.completion_pct}%"></progress>
                <small>{t.completion_pct}%</small>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</article>

<style>
  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    background: none;
    padding: 0;
    margin-bottom: 1rem;
  }

  h2 { margin: 0; }

  .table-wrap { overflow-x: auto; }

  .progress-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 10rem;
  }

  .progress-cell progress { flex: 1; }

  mark[data-tone='success'] { background: color-mix(in srgb, var(--color-success) 20%, transparent); color: var(--color-success); }
  mark[data-tone='warning'] { background: color-mix(in srgb, var(--color-warning) 20%, transparent); color: var(--color-warning); }
  mark[data-tone='error']   { background: color-mix(in srgb, var(--color-error)   20%, transparent); color: var(--color-error); }
</style>
