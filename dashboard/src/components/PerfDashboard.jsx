import { useEffect, useRef } from 'preact/compat';
import * as Plot from '@observablehq/plot';

export function PerfDashboard({ perfMetrics, qualityScores }) {
  const chartRef = useRef(null);
  const pieRef = useRef(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const latencies = perfMetrics?.causaganha_collect_latency_ms || [];
  const successRate = perfMetrics?.causaganha_upload_success_rate || 0;
  const backlogDays = perfMetrics?.causaganha_backlog_pending_days || 0;
  const activeTribunals = perfMetrics?.causaganha_active_tribunals || 0;
  const slowestTribunals = perfMetrics?.slowest_tribunals || [];
  const consecutiveFailures = perfMetrics?.causaganha_consecutive_failures || 0;
  const failureSeverity = perfMetrics?.causaganha_failure_severity;
  const lastFailingRunUrl = perfMetrics?.causaganha_last_failing_run_url;

  // Grade Distribution
  const gradeCounts = { A: 0, B: 0, C: 0, D: 0, F: 0 };
  if (qualityScores) {
    Object.values(qualityScores).forEach(score => {
      if (gradeCounts[score.grade] !== undefined) {
        gradeCounts[score.grade]++;
      }
    });
  }

  const gradeData = Object.entries(gradeCounts).map(([grade, count]) => ({ grade, count })).filter(d => d.count > 0);

  useEffect(() => {
    if (chartRef.current && latencies.length > 0) {
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

    if (pieRef.current && gradeData.length > 0) {
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
    return <div className="p-8 text-center text-gray-500">Loading performance data...</div>;
  }

  return (
    <div className="space-y-8">
      {consecutiveFailures > 0 && failureSeverity && (
        <div className={`p-4 rounded-xl border flex items-center justify-between ${
          failureSeverity === 'critical'
            ? 'bg-danger/10 border-danger text-danger dark:bg-danger/20 dark:text-red-400'
            : 'bg-warning/10 border-warning text-warning dark:bg-warning/20 dark:text-yellow-400'
        }`}>
          <div className="flex items-center gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <h3 className="font-semibold text-lg">
                Collect ZIPs {failureSeverity === 'critical' ? 'Critical Failure Streak' : 'Warning: Failing Streak'}
              </h3>
              <p className="text-sm">
                The pipeline has failed for {consecutiveFailures} consecutive runs.
              </p>
            </div>
          </div>
          {lastFailingRunUrl && (
            <a
              href={lastFailingRunUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                failureSeverity === 'critical'
                  ? 'bg-danger text-white hover:bg-red-600'
                  : 'bg-warning text-white hover:bg-yellow-600'
              }`}
            >
              View Last Run
            </a>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card text-center p-6">
          <div className="text-sm text-gray-500 mb-2">Upload Success Rate</div>
          <div className={`text-4xl font-bold ${successRate >= 90 ? 'text-success' : 'text-danger'}`}>
            {successRate.toFixed(1)}%
          </div>
        </div>

        <div className="card text-center p-6">
          <div className="text-sm text-gray-500 mb-2">Pending Backlog Days</div>
          <div className="text-4xl font-bold text-accent">
            {backlogDays}
          </div>
        </div>

        <div className="card text-center p-6">
          <div className="text-sm text-gray-500 mb-2">Active Tribunals</div>
          <div className="text-4xl font-bold text-black dark:text-white">
            {activeTribunals}
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Collection Latency Trend (7 days)</h3>
        <div ref={chartRef} className="w-full overflow-x-auto text-black dark:text-white" />
        {latencies.length === 0 && <div className="text-gray-500">No latency data available.</div>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Grade Distribution</h3>
          <div ref={pieRef} className="w-full text-black dark:text-white" />
        </div>

        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Top 5 Slowest Tribunals</h3>
          <ul className="space-y-4">
            {slowestTribunals.map((t, idx) => (
              <li key={t.tribunal} className="flex justify-between items-center border-b border-gray-100 dark:border-slate-800 pb-2">
                <span className="font-medium text-black dark:text-white">{idx + 1}. {t.tribunal}</span>
                <span className="text-sm text-gray-500">{t.velocity_14d.toFixed(1)} velocity (14d)</span>
              </li>
            ))}
            {slowestTribunals.length === 0 && <li className="text-gray-500">All tribunals are up to date!</li>}
          </ul>
        </div>
      </div>
    </div>
  );
}
