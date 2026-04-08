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

<style>
  .velocity-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .velocity-title {
    margin-bottom: 0;
  }

  .velocity-subtitle {
    opacity: 0.5;
    margin-bottom: 0;
    font-size: var(--font-size-sm);
  }

  .velocity-stats {
    text-align: right;
  }

  .velocity-current {
    font-weight: 700;
  }

  .velocity-trend {
    font-size: var(--font-size-sm);
  }

  .trend-success {
    color: var(--color-success);
  }

  .trend-error {
    color: var(--color-error);
  }

  .trend-neutral {
    opacity: 0.5;
  }

  .bar-chart {
    display: flex;
    align-items: flex-end;
    margin-top: 2.5rem;
    gap: 0.25rem;
    height: 100px;
  }

  .bar-slot {
    display: flex;
    align-items: flex-end;
    flex: 1;
    position: relative;
    height: 100%;
  }

  .bar-fill {
    width: 100%;
    border-radius: 0.25rem 0.25rem 0 0;
    opacity: 0.8;
    transition: opacity var(--transition-base);
  }

  .bar-labels {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    opacity: 0.5;
    margin-top: 0.5rem;
    font-size: var(--font-size-xs);
  }
</style>
