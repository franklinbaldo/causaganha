<script lang="ts">
  export let data: any = null;

  $: tribunals = data?.tribunals || [];

  // Filter for non-active states (Paused or Stopped)
  $: pausedTribunals = tribunals.filter((t: any) => t.state === 'Paused' || t.state === 'Stopped');

  $: updatedAt = data?.updated_at ? new Date(data.updated_at).toLocaleString('pt-BR') : 'N/A';

  function getDaysSinceDate(dateStr: string | null) {
    if (!dateStr) return 'Desconhecido';
    try {
      const pastDate = new Date(dateStr);
      if (isNaN(pastDate.getTime())) return 'Inválido';
      const today = new Date();
      // Set hours to 0 to compare just dates
      today.setHours(0, 0, 0, 0);
      pastDate.setHours(0, 0, 0, 0);

      const diffTime = Math.abs(today.getTime() - pastDate.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return `${diffDays} dia(s)`;
    } catch {
      return 'Erro';
    }
  }

  function getErrorMessage(result: string | null) {
    if (!result) return 'Sem mensagem de erro';
    if (result === 'error') return 'Erro de execução';
    return result;
  }
</script>

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body p-6">
    <div class="flex justify-between items-center mb-4">
      <h2 class="card-title text-xl">Tribunais Pausados ou Parados ({pausedTribunals.length})</h2>
      <span class="text-xs opacity-70">Atualizado: {updatedAt}</span>
    </div>

    {#if pausedTribunals.length === 0}
      <div class="alert alert-success">Todos os tribunais estão ativos! Não há tribunais pausados ou parados no momento.</div>
    {:else}
      <div class="table-responsive">
        <table class="table table-zebra w-full">
          <thead>
            <tr>
              <th>Tribunal</th>
              <th>Status Atual</th>
              <th>Mensagem de Erro</th>
              <th>Último Sucesso</th>
              <th>Data do Cursor</th>
            </tr>
          </thead>
          <tbody>
            {#each pausedTribunals as t}
              <tr>
                <td class="font-bold">{t.tribunal}</td>
                <td>
                  {#if t.state === 'Paused'}
                    <span class="badge badge-warning badge-sm">Pausado</span>
                  {:else if t.state === 'Stopped'}
                    <span class="badge badge-error badge-sm">Parado</span>
                  {:else}
                    <span class="badge badge-ghost badge-sm">{t.state}</span>
                  {/if}
                </td>
                <td class="text-sm opacity-90 text-error">{getErrorMessage(t.last_result)}</td>
                <td class="text-sm">{t.last_hit_date || 'Desconhecido'} <br><span class="text-xs opacity-60">({getDaysSinceDate(t.last_hit_date)})</span></td>
                <td class="font-mono text-sm">{t.cursor_date || 'N/A'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
