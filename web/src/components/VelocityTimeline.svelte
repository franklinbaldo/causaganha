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
      ? "trend-success"
      : currentVelocity < historicalAvgVelocity * 0.7
        ? "trend-error"
        : "trend-neutral"
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
    <div class="velocity-header">
      <div>
        <h4 class="velocity-title">Velocidade de Coleta</h4>
        <p class="velocity-subtitle">Taxa de coleta das últimas 12 semanas</p>
      </div>
      <div class="velocity-stats">
        <div class="velocity-current">{currentVelocity.toFixed(1)} dias/sem (média)</div>
        <div class="{trendColor} velocity-trend">
          {trend > 0 ? '+' : ''}{trend.toFixed(0)}% vs média ({trendText})
        </div>
      </div>
    </div>

    <div role="list" class="bar-chart">
      {#each weeklyData as week, idx}
        {@const heightPct = Math.max(5, (week.collected / maxCollected) * 100)}
        <div
          role="listitem"
          class="bar-slot"
          title="{week.collected} dias coletados (Semana {12 - week.weekOffset})"
          aria-label="{week.collected} dias coletados na semana {12 - week.weekOffset}">
          <div
            class="{getBarColor(week.collected)} bar-fill"
            style="height: {heightPct}%"></div>
        </div>
      {/each}
    </div>

    <div class="bar-labels">
      <span>12 semanas atrás</span>
      <span>Atual</span>
    </div>
  </div>
{/if}
