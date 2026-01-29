// GitHub Actions workflow run (used by RecentRuns component)
export interface GHWorkflowRun {
    id: number;
    name: string;
    run_number: number;
    status: 'queued' | 'in_progress' | 'completed';
    conclusion: 'success' | 'failure' | 'cancelled' | 'skipped' | null;
    created_at: string;
    html_url: string;
    display_title?: string;
}

// Parsed tribunal status (used by TribunalHeatmap component)
export interface TribunalStatus {
    tribunal: string;
    status: 'ok' | 'absent' | 'error' | 'pending';
    size?: number;
    fileCount?: number;
}
