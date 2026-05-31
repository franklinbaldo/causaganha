<script lang="ts">
  import * as Plot from '@observablehq/plot';
  import PipelineRunHistory from './PipelineRunHistory.svelte';

  interface LatencyEntry {
    date: string;
    latency_ms: number;
  }

  interface SlowestTribunal {
    tribunal: string;
    velocity_14d: number;
  }

  interface QualityScore {
    grade: string;
    [key: string]: unknown;
  }

  interface Props {
    perfMetrics: {
      causaganha_collect_latency_ms?: LatencyEntry[];
      causaganha_upload_success_rate?: number;
      causaganha_backlog_pending_days?: number;
      causaganha_active_tribunals?: number;
      slowest_tribunals?: SlowestTribunal[];
    } | null;
    qualityScores: Record<string, QualityScore> | null;
  }

  let { perfMetrics, qualityScores } = $props<Props>();

  let chartEl = $state<HTMLDivElement | undefined>(undefined);
  let pieEl = $state<HTMLDivElement | undefined>(undefined);

  const latencies = $derived(perfMetrics?.causaganha_collect_latency_ms || []);
  const successRate = $derived(perfMetrics?.causaganha_upload_success_rate || 0);
  const backlogDays = $derived(perfMetrics?.causaganha_backlog_pending_days || 0);
  const activeTribunals = $derived(perfMetrics?.causaganha_active_tribunals || 0);
  const slowestTribunals = $derived(perfMetrics?.slowest_tribunals || []);

  const gradeData = $derived.by(() => {
    const gradeCounts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, F: 0 };
    if (qualityScores) {
      Object.values(qualityScores).forEach((score: QualityScore) => {
        if (gradeCounts[score.grade] !== undefined) {
          gradeCounts[score.grade]++;
        }
      });
    }
    return Object.entries(gradeCounts)
      .map(([grade, count]) => ({ grade, count }))
      .filter((d) => d.count > 0);
  });

  $effect(() => {
    let chart: HTMLElement | SVGElement | null = null;
    let pie: HTMLElement | SVGElement | null = null;

    if (chartEl && latencies.length > 0) {
      const data = latencies.map((d) => ({
        date: new Date(d.date),
        latency: d.latency_ms / 60000,
      }));

      chart = Plot.plot({
        width: 800,
        height: 300,
        y: { label: 'Latency (minutes)', grid: true },
        x: { label: 'Date' },
        marks: [
          Plot.line(data, { x: 'date', y: 'latency', stroke: 'currentColor', strokeWidth: 2 }),
          Plot.dot(data, { x: 'date', y: 'latency', fill: 'currentColor', r: 4 }),
        ],
      });
      chartEl.replaceChildren(chart);
    }

    if (pieEl && gradeData.length > 0) {
      pie = Plot.plot({
        width: 400,
        height: 250,
        x: { label: 'Grade', domain: ['A', 'B', 'C', 'D', 'F'] },
        y: { label: 'Count', grid: true },
        color: {
          domain: ['A', 'B', 'C', 'D', 'F'],
          range: ['#10b981', '#3b82f6', '#eab308', '#f97316', '#ef4444'],
        },
        marks: [Plot.barY(gradeData, { x: 'grade', y: 'count', fill: 'grade' })],
      });
      pieEl.replaceChildren(pie);
    }

    return () => {
      if (chart) chart.remove();
      if (pie) pie.remove();
    };
  });
</script>

{#if !perfMetrics || !qualityScores}
  <p aria-live="polite" aria-busy="true">Carregando dados de desempenho...</p>
{:else}
  <div>
    <div class="auto-grid">
      <article>
        <small>Taxa de sucesso de upload</small>
        <div data-tone={successRate >= 90 ? 'success' : 'error'}>
          {successRate.toFixed(1)}%
        </div>
      </article>

      <article>
        <small>Dias de backlog pendente</small>
        <div>
          {backlogDays}
        </div>
      </article>

      <article>
        <small>Tribunais ativos</small>
        <div>
          {activeTribunals}
        </div>
      </article>
    </div>

    <article>
      <h3>Tendência de latência de coleta (7 dias)</h3>
      <div bind:this={chartEl}></div>
      {#if latencies.length === 0}
        <p>Sem dados de latência disponíveis.</p>
      {/if}
    </article>

    <div class="auto-grid">
      <article>
        <h3>Distribuição por nota</h3>
        <div bind:this={pieEl}></div>
      </article>

      <article>
        <h3>5 tribunais mais lentos</h3>
        <ol>
          {#each slowestTribunals as t, idx}
            <li>
              <span>{idx + 1}. {t.tribunal}</span>
              <span>velocidade {t.velocity_14d.toFixed(1)} (14d)</span>
            </li>
          {/each}
          {#if slowestTribunals.length === 0}
            <li>Todos os tribunais estão atualizados!</li>
          {/if}
        </ol>
      </article>
    </div>

    <div>
      <PipelineRunHistory />
    </div>
  </div>
{/if}
