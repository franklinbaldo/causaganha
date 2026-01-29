import { useState, useEffect } from 'react';
import { LINKS, LABELS } from '../lib/constants';
import { formatBytes } from '../lib/utils';
import { fetchDashboardCache, extractRecentDays } from '../lib/api';

interface DayData {
    date: string;
    size: number;
    tribunalCount: number;
    exists: boolean;
}

export default function RecentDays() {
    const [days, setDays] = useState<DayData[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            const cache = await fetchDashboardCache();
            if (cache) {
                setDays(extractRecentDays(cache, 5));
            }
            setLoading(false);
        }
        loadData();
    }, []);

    if (loading) {
        return (
            <div className="space-y-3">
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                        <div className="skeleton w-2 h-2 rounded-full" />
                        <div className="skeleton h-4 flex-1 rounded" />
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {days.map((day) => (
                <a
                    key={day.date}
                    href={day.exists ? LINKS.IA_DETAILS(day.date) : undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`
            flex items-center gap-3 p-2 -mx-2 rounded-lg transition-colors
            ${day.exists ? 'hover:bg-border-hover/50 cursor-pointer' : 'opacity-50 cursor-default'}
          `}
                >
                    <div className={`w-2 h-2 rounded-full ${day.exists ? 'bg-accent-green' : 'bg-text-muted'}`} />
                    <div className="flex-1 min-w-0">
                        <span className="text-sm font-mono text-text-primary">{day.date}</span>
                    </div>
                    {day.exists && (
                        <div className="flex items-center gap-3 text-xs text-text-muted shrink-0">
                            <span>{day.tribunalCount} tribunais</span>
                            <span className="font-mono">{formatBytes(day.size)}</span>
                        </div>
                    )}
                </a>
            ))}
        </div>
    );
}
