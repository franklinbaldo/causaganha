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
    <div  role="status" aria-label="Workflow in progress">
      <span>
        <span></span>
        <span></span>
      </span>
      <span>Coletando agora...</span>
      <span>
        {formatElapsed(status.elapsedMs)}
      </span>
    </div>
  );
}
