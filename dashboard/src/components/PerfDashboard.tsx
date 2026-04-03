import { useEffect, useMemo, useRef } from 'preact/compat';
import * as Plot from '@observablehq/plot';
import { LiveStatusWidget } from './LiveStatusWidget';
import { PipelineRunHistory } from './PipelineRunHistory';

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

export function PerfDashboard({ perfMetrics, qualityScores }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const pieRef = useRef<HTMLDivElement>(null);

  const latencies = useMemo<LatencyEntry[]>(
    () => (perfMetrics?.causaganha_collect_latency_ms || []),
    [perfMetrics]
  );
  const successRate: number = perfMetrics?.causaganha_upload_success_rate || 0;
  const backlogDays: number = perfMetrics?.causaganha_backlog_pending_days || 0;
  const activeTribunals: number = perfMetrics?.causaganha_active_tribunals || 0;
  const slowestTribunals: SlowestTribunal[] = perfMetrics?.slowest_tribunals || [];

  // Grade Distribution
  const gradeData = useMemo(() => {
    const gradeCounts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, F: 0 };
    if (qualityScores) {
      Object.values(qualityScores).forEach((score: QualityScore) => {
        if (gradeCounts[score.grade] !== undefined) {
          gradeCounts[score.grade]++;
        }
      });
    }
    return Object.entries(gradeCounts).map(([grade, count]) => ({ grade, count })).filter(d => d.count> 0);
  }, [qualityScores]);

  useEffect(() => {
    if (chartRef.current && latencies.length> 0) {
      const data = latencies.map(d => ({
        date: new Date(d.date),
        latency: d.latency_ms / 60000 // Convert to minutes
      }));

      const chart = Plot.plot({
        width: 800,
        height: 300,
        y: { label: "Latency (minutes)", grid: true },
        x: { label: "Date" },
        marks: [
          Plot.line(data, { x: "date", y: "latency", stroke: "currentColor", strokeWidth: 2 }),
          Plot.dot(data, { x: "date", y: "latency", fill: "currentColor", r: 4 })
        ]
      });
      chartRef.current.innerHTML = "";
      chartRef.current.appendChild(chart);
    }

    if (pieRef.current && gradeData.length> 0) {
      // Basic pie representation using Plot.rect or similar, or just D3. Observable plot 0.6 has some support but let's use a simple bar for distribution since Plot doesn't do pie easily out of the box in this version
      const pie = Plot.plot({
        width: 400,
        height: 250,
        x: { label: "Grade", domain: ["A", "B", "C", "D", "F"] },
        y: { label: "Count", grid: true },
        color: {
          domain: ["A", "B", "C", "D", "F"],
          range: ["#10b981", "#3b82f6", "#eab308", "#f97316", "#ef4444"] // cyber.success, info, warning...
        },
        marks: [
          Plot.barY(gradeData, { x: "grade", y: "count", fill: "grade" })
        ]
      });
      pieRef.current.innerHTML = "";
      pieRef.current.appendChild(pie);
    }
  }, [latencies, gradeData]);

  if (!perfMetrics || !qualityScores) {
    return <div>Loading performance data...</div>;
  }

  return (
    <div>
      <div>
        <LiveStatusWidget />
      </div>

      <div className="grid">
        <article>
          <small>Upload Success Rate</small>
          <div className={successRate >= 90 ? 'text-success' : 'text-danger'}>
            {successRate.toFixed(1)}%
          </div>
        </article>

        <article>
          <small>Pending Backlog Days</small>
          <div className="text-accent">
            {backlogDays}
          </div>
        </article>

        <article>
          <small>Active Tribunals</small>
          <div>
            {activeTribunals}
          </div>
        </article>
      </div>

      <article>
        <h3>Collection Latency Trend (7 days)</h3>
        <div ref={chartRef} />
        {latencies.length === 0 && <div>No latency data available.</div>}
      </article>

      <div className="grid">
        <article>
          <h3>Grade Distribution</h3>
          <div ref={pieRef} />
        </article>

        <article>
          <h3>Top 5 Slowest Tribunals</h3>
          <ul>
            {slowestTribunals.map((t, idx) => (
              <li key={t.tribunal}>
                <span>{idx + 1}. {t.tribunal}</span>
                <span>{t.velocity_14d.toFixed(1)} velocity (14d)</span>
              </li>
            ))}
            {slowestTribunals.length === 0 && <li>All tribunals are up to date!</li>}
          </ul>
        </article>
      </div>

      <div>
        <PipelineRunHistory />
      </div>
    </div>
  );
}
