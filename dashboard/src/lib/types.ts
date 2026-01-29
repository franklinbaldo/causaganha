// Internet Archive metadata response
export interface IAMetadata {
    item_size?: number;
    files_count?: number;
    metadata?: {
        identifier: string;
        date: string;
        title: string;
    };
    files?: IAFile[];
}

export interface IAFile {
    name: string;
    size: string;
    format: string;
    filecount?: string;
}

// GitHub Actions response
export interface GHActionsResponse {
    total_count: number;
    workflow_runs: GHWorkflowRun[];
}

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

// Parsed tribunal status
export interface TribunalStatus {
    tribunal: string;
    status: 'ok' | 'absent' | 'error' | 'pending';
    size?: number;
    fileCount?: number;
}

// Day summary
export interface DaySummary {
    date: string;
    itemSize: number;
    tribunalCount: number;
    tribunals: TribunalStatus[];
    exists: boolean;
}

// Calendar cell data
export interface CalendarCell {
    date: string;
    level: 0 | 1 | 2 | 3 | 4;
    size: number;
    tribunalCount: number;
    isFuture: boolean;
}
