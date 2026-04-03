import { useState, useEffect } from 'preact/hooks';

// We can directly use the workflow filename instead of fetching the ID first
const WORKFLOW_ID = 'collect-zips.yml';
const REPO = 'franklinbaldo/causaganha';
const API_URL = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_ID}/runs?status=in_progress`;

export function useWorkflowStatus(pollInterval = 60000) {
  const [status, setStatus] = useState({
    isRunning: false,
    startedAt: null,
    elapsedMs: 0,
    error: null,
  });

  useEffect(() => {
    let isMounted = true;
    let timerId = null;

    const fetchStatus = async () => {
      try {
        const response = await fetch(API_URL);
        if (!response.ok) {
          throw new Error(`GitHub API error: ${response.status}`);
        }

        const data = await response.json();

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
      } catch (err) {
        if (!isMounted) return;
        // Graceful error handling: don't crash, just hide the badge
        setStatus(prev => ({
          ...prev,
          isRunning: false,
          error: err.message
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
    let elapsedTimerId = null;

    if (status.isRunning && status.startedAt) {
      elapsedTimerId = setInterval(() => {
        setStatus(prev => ({
          ...prev,
          elapsedMs: Date.now() - prev.startedAt
        }));
      }, 1000);
    }

    return () => {
      if (elapsedTimerId) clearInterval(elapsedTimerId);
    };
  }, [status.isRunning, status.startedAt]);

  return status;
}
