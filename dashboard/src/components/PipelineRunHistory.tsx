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
      return <span className="text-yellow-500 animate-pulse" title="In Progress">⏳</span>;
    }
    if (conclusion === 'success') {
      return <span className="text-green-500" title="Success">✅</span>;
    }
    return <span className="text-red-500" title="Failure">❌</span>;
  };

  const calculateDuration = (createdAt: string, updatedAt: string): number => {
    const start = new Date(createdAt);
    const end = new Date(updatedAt);
    const diffMs = end.getTime() - start.getTime();
    const diffMins = Math.round(diffMs / 60000);
    return diffMins;
  };

  return (
    <div className="card p-6 mt-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Pipeline Run History (Collect ZIPs)</h3>

      {loading && <div className="text-gray-500">Loading run history...</div>}

      {error && <div className="text-red-500">Error: {error}</div>}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-200 dark:border-slate-700">
                <th className="py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Run Date</th>
                <th className="py-3 px-4 font-medium text-gray-700 dark:text-gray-300">Duration (min)</th>
                <th className="py-3 px-4 font-medium text-gray-700 dark:text-gray-300 text-center">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-gray-100 dark:border-slate-800 hover:bg-gray-50 dark:hover:bg-slate-800/50">
                  <td className="py-3 px-4 text-gray-800 dark:text-gray-200">
                    <a href={run.html_url} target="_blank" rel="noopener noreferrer" className="hover:text-blue-500 hover:underline">
                      {new Date(run.created_at).toLocaleString()}
                    </a>
                  </td>
                  <td className="py-3 px-4 text-gray-600 dark:text-gray-400">
                    {calculateDuration(run.created_at, run.updated_at)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {getStatusIcon(run.status, run.conclusion)}
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={3} className="py-4 text-center text-gray-500">No runs found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
