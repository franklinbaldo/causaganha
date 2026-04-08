import { writable, type Readable } from 'svelte/store';

export interface WorkflowStatus {
  isRunning: boolean;
  startedAt: number | null;
  elapsedMs: number;
  error: string | null;
}

const WORKFLOW_ID = 'collect-zips.yml';
const REPO = 'franklinbaldo/causaganha';
const API_URL = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW_ID}/runs?status=in_progress`;

/**
 * Creates a Svelte store for GitHub Actions workflow status polling.
 * Use start()/stop() in onMount/onDestroy.
 */
export function createWorkflowStatus(pollInterval: number = 60000) {
  const { subscribe, update } = writable<WorkflowStatus>({
    isRunning: false,
    startedAt: null,
    elapsedMs: 0,
    error: null,
  });

  let pollTimer: ReturnType<typeof setInterval> | null = null;
  let elapsedTimer: ReturnType<typeof setInterval> | null = null;
  let destroyed = false;

  async function fetchStatus(): Promise<void> {
    try {
      const response = await fetch(API_URL);
      if (!response.ok) {
        throw new Error(`GitHub API error: ${response.status}`);
      }

      const data: any = await response.json();
      if (destroyed) return;

      if (data.total_count > 0 && data.workflow_runs?.length > 0) {
        const run = data.workflow_runs[0];
        const startedAtTime = new Date(run.run_started_at).getTime();

        update(prev => ({
          ...prev,
          isRunning: true,
          startedAt: startedAtTime,
          elapsedMs: Date.now() - startedAtTime,
          error: null,
        }));
        startElapsedTimer();
      } else {
        update(prev => ({
          ...prev,
          isRunning: false,
          startedAt: null,
          elapsedMs: 0,
          error: null,
        }));
        stopElapsedTimer();
      }
    } catch (err: unknown) {
      if (destroyed) return;
      update(prev => ({
        ...prev,
        isRunning: false,
        error: err instanceof Error ? err.message : String(err),
      }));
    }
  }

  function startElapsedTimer(): void {
    stopElapsedTimer();
    elapsedTimer = setInterval(() => {
      update(prev => ({
        ...prev,
        elapsedMs: prev.startedAt ? Date.now() - prev.startedAt : 0,
      }));
    }, 1000);
  }

  function stopElapsedTimer(): void {
    if (elapsedTimer) {
      clearInterval(elapsedTimer);
      elapsedTimer = null;
    }
  }

  function start(): void {
    destroyed = false;
    fetchStatus();
    pollTimer = setInterval(fetchStatus, pollInterval);
  }

  function stop(): void {
    destroyed = true;
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
    stopElapsedTimer();
  }

  return {
    subscribe,
    start,
    stop,
  };
}
