<script lang="ts">
  import { getBarColor } from '../lib/colorUtils';

  interface VelocityWeek {
    collected: number;
    weekOffset: number;
  }

  interface VelocityTimelineProps {
    metrics: any;
  }

  let { metrics }: VelocityTimelineProps = $props();

  let show = $derived(metrics && metrics.hasEnoughHistory);

  let weeklyData = $derived(show ? metrics.weeklyData : []);
  let historicalAvgVelocity = $derived(show ? metrics.historicalAvgVelocity : 0);
  let currentVelocity = $derived(show ? metrics.currentVelocity : 0);
  let trend = $derived(show ? metrics.trend : 0);
  let maxCollected = $derived(Math.max(7, ...weeklyData.map((w: VelocityWeek) => w.collected)));

  let trendColor = $derived(
    currentVelocity > historicalAvgVelocity * 1.2
      ? "text-success"
      : currentVelocity < historicalAvgVelocity * 0.7
        ? "text-error"
        : "opacity-50"
  );

  let trendText = $derived(
    currentVelocity > historicalAvgVelocity * 1.2
      ? "Acelerando"
      : currentVelocity < historicalAvgVelocity * 0.7
        ? "Em declínio"
        : "Estável"
  );
</script>

{#if show}
  <div aria-label="Velocidade de Coleta nas Últimas 12 Semanas">
    <div class="flex justify-between items-baseline flex-wrap gap-4 mb-6 items-baseline">
      <div>
        <h4 class="mb-0">Velocidade de Coleta</h4>
        <p class="opacity-50 mb-0 text-sm">Taxa de coleta das últimas 12 semanas</p>
      </div>
      <div class="text-right">
        <div class="font-bold">{currentVelocity.toFixed(1)} dias/sem (média)</div>
        <div class="{trendColor} text-sm">
          {trend > 0 ? '+' : ''}{trend.toFixed(0)}% vs média ({trendText})
        </div>
      </div>
    </div>

    <div role="list" class="flex items-end mt-10 gap-1 h-[100px]">
      {#each weeklyData as week, idx}
        {@const heightPct = Math.max(5, (week.collected / maxCollected) * 100)}
        <div
          role="listitem"
          class="flex items-end flex-1 relative h-full"
          title="{week.collected} dias coletados (Semana {12 - week.weekOffset})"
          aria-label="{week.collected} dias coletados na semana {12 - week.weekOffset}">
          <div
            class="{getBarColor(week.collected)} w-full rounded-t opacity-80 transition-opacity"
            style="height: {heightPct}%"></div>
        </div>
      {/each}
    </div>

    <div class="flex justify-between items-baseline opacity-50 mt-2 text-xs">
      <span>12 semanas atrás</span>
      <span>Atual</span>
    </div>
  </div>
{/if}
