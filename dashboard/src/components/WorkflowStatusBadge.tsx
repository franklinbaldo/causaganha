import { useWorkflowStatus } from '../lib/useWorkflowStatus';

// Format milliseconds to MM:SS
function formatElapsed(ms: number): string {
  if (!ms || ms < 0) return '00:00';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

export function WorkflowStatusBadge() {
  const status = useWorkflowStatus();

  if (!status.isRunning) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-800 shadow-sm text-sm font-medium mr-2" role="status" aria-label="Workflow in progress">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-500 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600 dark:bg-blue-400"></span>
      </span>
      <span>Coletando agora...</span>
      <span className="font-mono bg-blue-100 dark:bg-blue-800/50 px-1.5 rounded text-xs ml-1">
        {formatElapsed(status.elapsedMs)}
      </span>
    </div>
  );
}
