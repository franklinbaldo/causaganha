import { useState, useEffect } from 'preact/compat';

interface WorkflowStatus {
  isRunning: boolean;
  startedAt: number | null;
  elapsedMs: number;
  error: string | null;
}

// We can directly use the workflow filename instead of fetching the ID first
const WORKFLOW_ID = 'collect-zips.yml';
const REPO = 'franklinbaldo/causaganha';
const API_URL = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_ID}/runs?status=in_progress`;

export function useWorkflowStatus(pollInterval: number = 60000): WorkflowStatus {
  const [status, setStatus] = useState<WorkflowStatus>({
    isRunning: false,
    startedAt: null,
    elapsedMs: 0,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const fetchStatus = async (): Promise<void> => {
      try {
        const response = await fetch(API_URL);
        if (!response.ok) {
          throw new Error(`GitHub API error: ${response.status}`);
        }

        const data: any = await response.json();

        if (!isMounted) return;

        if (data.total_count > 0 && data.workflow_runs && data.workflow_runs.length > 0) {
          // Get the oldest running one if multiple are running, or just the first
          const run = data.workflow_runs[0];
          const startedAt = new Date(run.run_started_at).getTime();

          setStatus(prev => ({
            ...prev,
            isRunning: true,
            startedAt,
            elapsedMs: Date.now() - startedAt,
            error: null
          }));
        } else {
          setStatus(prev => ({
            ...prev,
            isRunning: false,
            startedAt: null,
            elapsedMs: 0,
            error: null
          }));
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        // Graceful error handling: don't crash, just hide the badge
        setStatus(prev => ({
          ...prev,
          isRunning: false,
          error: err instanceof Error ? err.message : String(err)
        }));
      }
    };

    // Initial fetch
    fetchStatus();

    // Polling setup
    timerId = setInterval(fetchStatus, pollInterval);

    return () => {
      isMounted = false;
      if (timerId) clearInterval(timerId);
    };
  }, [pollInterval]);

  // Separate effect for updating the elapsed time every second if running
  useEffect(() => {
    let elapsedTimerId: ReturnType<typeof setInterval> | null = null;

    if (status.isRunning && status.startedAt) {
      elapsedTimerId = setInterval(() => {
        setStatus(prev => ({
          ...prev,
          elapsedMs: prev.startedAt ? Date.now() - prev.startedAt : 0
        }));
      }, 1000);
    }

    return () => {
      if (elapsedTimerId) clearInterval(elapsedTimerId);
    };
  }, [status.isRunning, status.startedAt]);

  return status;
}
