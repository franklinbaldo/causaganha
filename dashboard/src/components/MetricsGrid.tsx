import { useState, useEffect } from 'react';
import { LABELS } from '../lib/constants';
import { formatBytes } from '../lib/utils';
import { fetchDashboardCache, getCacheAge } from '../lib/api';

interface MetricsData {
    filesToday: number;
    sizeToday: number;
    daysArchived: number;
    health: number;
    cacheAge?: string;
}

export default function MetricsGrid() {
    const [data, setData] = useState<MetricsData>({ filesToday: 0, sizeToday: 0, daysArchived: 0, health: 0 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadData() {
            const cache = await fetchDashboardCache();
            if (cache) {
                setData({
                    filesToday: cache.today.files_today,
                    sizeToday: cache.today.size_today,
                    daysArchived: cache.today.days_archived,
                    health: cache.today.health,
                    cacheAge: getCacheAge(cache.meta.generated_at),
                });
            }
            setLoading(false);
        }
        loadData();
    }, []);

    const metrics = [
        {
            title: LABELS.metrics.files.title,
            subtitle: LABELS.metrics.files.subtitle,
            value: data.filesToday,
            color: data.filesToday > 0 ? 'text-accent-green' : 'text-text-primary',
        },
        {
            title: LABELS.metrics.size.title,
            subtitle: LABELS.metrics.size.subtitle,
            value: formatBytes(data.sizeToday),
            color: 'text-text-primary',
        },
        {
            title: LABELS.metrics.days.title,
            subtitle: LABELS.metrics.days.subtitle,
            value: `~${data.daysArchived}`,
            color: 'text-text-primary',
        },
        {
            title: LABELS.metrics.health.title,
            subtitle: LABELS.metrics.health.subtitle,
            value: `${data.health}%`,
            color: data.health >= 80 ? 'text-accent-green' : data.health >= 50 ? 'text-accent-yellow' : 'text-accent-red',
        },
    ];

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics.map((metric, i) => (
                <div
                    key={i}
                    className="bg-card border border-border rounded-xl p-6 card-glow transition-all duration-200 hover:border-border-hover animate-slide-up"
                    style={{ animationDelay: `${i * 50}ms` }}
                >
                    <div className="space-y-2">
                        <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                            {metric.title}
                        </p>
                        <div className="h-10 flex items-baseline">
                            {loading ? (
                                <div className="skeleton h-8 w-20 rounded" />
                            ) : (
                                <p className={`text-3xl font-mono font-bold tabular-nums ${metric.color}`}>
                                    {metric.value}
                                </p>
                            )}
                        </div>
                        <p className="text-sm text-text-muted">
                            {metric.subtitle}
                        </p>
                    </div>
                </div>
            ))}
        </div>
    );
}
