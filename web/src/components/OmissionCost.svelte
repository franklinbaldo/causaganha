<script lang="ts">
  type OmissionStats = {
    global_omission_cost: number;
    tribunals: Record<string, number>;
    generated_at: string;
  };

  let { omissionStats }: { omissionStats: OmissionStats | null } = $props();

  let globalOmissionCost = $derived(omissionStats?.global_omission_cost || 0);

  let rankedTribunals = $derived(() => {
    if (!omissionStats?.tribunals) return [];
    return Object.entries(omissionStats.tribunals)
      .map(([tribunal, count]) => ({ tribunal, count }))
      .sort((a, b) => b.count - a.count);
  });
</script>

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body">
    <h2 class="card-title text-xl mb-4">Omission Cost</h2>

    {#if !omissionStats}
      <div class="text-center py-4 opacity-70" aria-busy="true">
        Carregando dados...
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Global Stats -->
        <div class="md:col-span-1 flex flex-col justify-center items-center p-6 bg-base-200 rounded-lg">
          <span class="text-sm uppercase tracking-wider opacity-70 mb-2">Global Omission Cost</span>
          <span class="text-5xl font-bold text-error">{globalOmissionCost}</span>
          <span class="text-xs opacity-50 mt-4">Dias úteis perdidos (sem .zip ou .absent)</span>
        </div>

        <!-- Ranked Tribunals Table -->
        <div class="md:col-span-2">
          <div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
            <table class="table table-zebra table-sm w-full">
              <thead class="sticky top-0 bg-base-100 z-10">
                <tr>
                  <th class="text-left w-12">#</th>
                  <th class="text-left">Tribunal</th>
                  <th class="text-right">Dias Omitidos</th>
                  <th class="w-24"></th>
                </tr>
              </thead>
              <tbody>
                {#each rankedTribunals() as {tribunal, count}, i}
                  <tr>
                    <td class="opacity-50">{i + 1}</td>
                    <td class="font-medium">{tribunal}</td>
                    <td class="text-right font-mono">{count}</td>
                    <td>
                      <!-- Simple bar chart visualization -->
                      <div class="w-full bg-base-200 rounded-full h-2">
                        <div
                          class="bg-error h-2 rounded-full"
                          style="width: {Math.min(100, Math.max(1, (count / (rankedTribunals()[0]?.count || 1)) * 100))}%"
                        ></div>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>
