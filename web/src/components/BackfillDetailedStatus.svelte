<script lang="ts">
  let { data = null }: { data: any } = $props();

  let tribunals = $derived(data?.tribunals || []);
  let updatedAt = $derived(data?.updated_at ? new Date(data.updated_at).toLocaleString('pt-BR') : 'N/A');
</script>

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body p-6">
    <div class="flex justify-between items-center mb-4">
      <h2 class="card-title text-xl">Detalhes de Backfill por Tribunal</h2>
      <span class="text-xs opacity-70">Última verificação: {updatedAt}</span>
    </div>

    {#if tribunals.length === 0}
      <div class="alert alert-info">Nenhum dado de backfill disponível.</div>
    {:else}
      <div class="table-responsive">
        <table class="table table-zebra w-full">
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
                <td class="font-bold">{t.tribunal}</td>
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
                <td class="text-xs opacity-80">{t.genesis_date}</td>
                <td class="font-mono text-sm">{t.cursor_date || 'N/A'}</td>
                <td class="w-1/3 min-w-[150px]">
                  <div class="flex items-center gap-2">
                    <progress class="progress flex-1" value={t.completion_pct} max="100"></progress>
                    <span class="text-xs font-medium w-10 text-right">{t.completion_pct}%</span>
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
