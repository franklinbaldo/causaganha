import { useState, useEffect } from 'preact/compat';
import type { JSX } from 'preact';

interface WorkflowRun {
  id: number;
  status: string;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  html_url: string;
}

interface WorkflowRunsResponse {
  workflow_runs: WorkflowRun[];
}

export function PipelineRunHistory() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const response = await fetch('https://api.github.com/repos/franklinbaldo/causaganha/actions/workflows/collect-zips.yml/runs?per_page=7');
        if (!response.ok) {
          throw new Error(`Failed to fetch runs: ${response.status} ${response.statusText}`);
        }
        const data: WorkflowRunsResponse = await response.json();
        setRuns(data.workflow_runs || []);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    };

    fetchRuns();
  }, []);

  const getStatusIcon = (status: string, conclusion: string | null): JSX.Element => {
    if (status !== 'completed') {
      return <span  title="In Progress">⏳</span>;
    }
    if (conclusion === 'success') {
      return <span  title="Success">✅</span>;
    }
    return <span  title="Failure">❌</span>;
  };

  const calculateDuration = (createdAt: string, updatedAt: string): number => {
    const start = new Date(createdAt);
    const end = new Date(updatedAt);
    const diffMs = end.getTime() - start.getTime();
    const diffMins = Math.round(diffMs / 60000);
    return diffMins;
  };

  return (
    <div className="card">
      <h3>Pipeline Run History (Collect ZIPs)</h3>

      {loading && <div>Loading run history...</div>}

      {error && <div>Error: {error}</div>}

      {!loading && !error && (
        <div>
          <table className="text-left">
            <thead>
              <tr>
                <th>Run Date</th>
                <th>Duration (min)</th>
                <th className="text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>
                    <a href={run.html_url} target="_blank" rel="noopener noreferrer">
                      {new Date(run.created_at).toLocaleString()}
                    </a>
                  </td>
                  <td>
                    {calculateDuration(run.created_at, run.updated_at)}
                  </td>
                  <td className="text-center">
                    {getStatusIcon(run.status, run.conclusion)}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={3} className="text-center">No runs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
