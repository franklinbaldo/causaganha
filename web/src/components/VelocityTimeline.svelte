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
    <div>
      <div>
        <h4>Velocidade de Coleta</h4>
        <small>Taxa de coleta das últimas 12 semanas</small>
      </div>
      <div class="auto-grid-sm">
        <strong class="stat-value">{currentVelocity.toFixed(1)} dias/sem (média)</strong>
        <span data-tone={trendColor === 'trend-success' ? 'success' : trendColor === 'trend-error' ? 'error' : 'muted'}>
          {trend > 0 ? '+' : ''}{trend.toFixed(0)}% vs média ({trendText})
        </span>
      </div>
    </div>

    <div role="list">
      {#each weeklyData as week, idx}
        {@const heightPct = Math.max(5, (week.collected / maxCollected) * 100)}
        <div
          role="listitem"
          title="{week.collected} dias coletados (Semana {12 - week.weekOffset})"
          aria-label="{week.collected} dias coletados na semana {12 - week.weekOffset}">
          <div
            class={getBarColor(week.collected)}
            style="height: {heightPct}%"></div>
        </div>
      {/each}
    </div>

    <div>
      <small>12 semanas atrás</small>
      <small>Atual</small>
    </div>
  </div>
{/if}
