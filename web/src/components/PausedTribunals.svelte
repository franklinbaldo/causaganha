<script lang="ts">
  let { data = null }: { data: any } = $props();

  const tribunals = $derived(data?.tribunals || []);
  const pausedTribunals = $derived(tribunals.filter((t: any) => t.state === 'Paused' || t.state === 'Stopped'));
  const updatedAt = $derived(data?.updated_at ? new Date(data.updated_at).toLocaleString('pt-BR') : 'N/A');

  function getDaysSinceDate(dateStr: string | null) {
    if (!dateStr) return 'Desconhecido';
    try {
      const pastDate = new Date(dateStr);
      if (isNaN(pastDate.getTime())) return 'Inválido';
      const today = new Date();
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

<article>
  <header>
    <h2>Tribunais Pausados ou Parados ({pausedTribunals.length})</h2>
    <small>Atualizado: {updatedAt}</small>
  </header>

  {#if pausedTribunals.length === 0}
    <p>Todos os tribunais estão ativos! Não há tribunais pausados ou parados no momento.</p>
  {:else}
    <div class="table-wrap">
      <table>
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
              <td><strong>{t.tribunal}</strong></td>
              <td>
                {#if t.state === 'Paused'}
                  <mark class="tone-warning">Pausado</mark>
                {:else if t.state === 'Stopped'}
                  <mark class="tone-error">Parado</mark>
                {:else}
                  <mark>{t.state}</mark>
                {/if}
              </td>
              <td class="error-msg">{getErrorMessage(t.last_result)}</td>
              <td>
                {t.last_hit_date || 'Desconhecido'}
                <br><small>({getDaysSinceDate(t.last_hit_date)})</small>
              </td>
              <td><kbd>{t.cursor_date || 'N/A'}</kbd></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</article>
