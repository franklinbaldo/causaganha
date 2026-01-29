import { useState, useEffect } from 'react';
import { API, LABELS } from '../lib/constants';
import { timeAgo } from '../lib/utils';
import type { GHWorkflowRun } from '../lib/types';

const STATUS_ICONS = {
    success: (
        <svg className="w-4 h-4 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
    ),
    failure: (
        <svg className="w-4 h-4 text-accent-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
    ),
    cancelled: (
        <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
        </svg>
    ),
    in_progress: (
        <svg className="w-4 h-4 text-accent-yellow animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
    ),
};

export default function RecentRuns() {
    const [runs, setRuns] = useState<GHWorkflowRun[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        async function fetchRuns() {
            try {
                const res = await fetch(API.GH_RUNS);
                if (!res.ok) throw new Error('Failed to fetch');
                const data = await res.json();
                setRuns((data.workflow_runs || []).slice(0, 8));
                setError(false);
            } catch {
                setError(true);
            } finally {
                setLoading(false);
            }
        }

        fetchRuns();
        const interval = setInterval(fetchRuns, 2 * 60 * 1000); // Refresh every 2 minutes
        return () => clearInterval(interval);
    }, []);

    const getStatusIcon = (run: GHWorkflowRun) => {
        if (run.status === 'in_progress' || run.status === 'queued') {
            return STATUS_ICONS.in_progress;
        }
        return STATUS_ICONS[run.conclusion as keyof typeof STATUS_ICONS] || STATUS_ICONS.cancelled;
    };

    if (loading) {
        return (
            <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                        <div className="skeleton w-4 h-4 rounded-full" />
                        <div className="skeleton h-4 flex-1 rounded" />
                    </div>
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div className="text-sm text-text-muted text-center py-4">
                {LABELS.error.loading}
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {runs.map((run) => (
                <a
                    key={run.id}
                    href={run.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-2 -mx-2 rounded-lg transition-colors hover:bg-border-hover/50"
                >
                    {getStatusIcon(run)}
                    <div className="flex-1 min-w-0">
                        <div className="text-sm text-text-primary truncate">
                            {run.display_title || run.name}
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-text-muted shrink-0">
                        <span className="font-mono">#{run.run_number}</span>
                        <span>{timeAgo(run.created_at)}</span>
                    </div>
                </a>
            ))}
        </div>
    );
}
