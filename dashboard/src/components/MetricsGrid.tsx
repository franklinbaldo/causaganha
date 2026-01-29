import { useState, useEffect } from 'react';
import { API, LABELS } from '../lib/constants';
import { formatBytes, getToday } from '../lib/utils';
import { fetchPreBuiltCache, getCacheAge } from '../lib/api';

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
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        // Step 1: Load pre-built cache immediately (instant data)
        async function loadCache() {
            const cache = await fetchPreBuiltCache();
            if (cache) {
                setData({
                    filesToday: cache.today.files_today,
                    sizeToday: cache.today.size_today,
                    daysArchived: cache.today.days_archived,
                    health: cache.today.health,
                    cacheAge: getCacheAge(cache.meta.generated_at),
                });
                setLoading(false);
            }
        }

        // Step 2: Fetch live data in background
        async function fetchLiveMetrics() {
            setRefreshing(true);
            try {
                // Fetch today's IA metadata
                const todayRes = await fetch(API.IA_METADATA(getToday()));
                let filesToday = data.filesToday;
                let sizeToday = data.sizeToday;

                if (todayRes.ok) {
                    const todayData = await todayRes.json();
                    const zipFiles = (todayData.files || []).filter((f: any) => f.name.endsWith('.zip'));
                    filesToday = zipFiles.length;
                    sizeToday = todayData.item_size || 0;
                }

                // Fetch GitHub Actions health
                const ghRes = await fetch(API.GH_RUNS);
                let health = data.health;
                if (ghRes.ok) {
                    const ghData = await ghRes.json();
                    const runs = ghData.workflow_runs || [];
                    const successful = runs.filter((r: any) => r.conclusion === 'success').length;
                    health = runs.length > 0 ? Math.round((successful / runs.length) * 100) : 0;
                }

                setData(prev => ({
                    ...prev,
                    filesToday,
                    sizeToday,
                    health,
                    cacheAge: undefined // Clear cache age when showing live data
                }));
            } catch (error) {
                console.error('Failed to fetch live metrics:', error);
            } finally {
                setLoading(false);
                setRefreshing(false);
            }
        }

        // Load cache first (fast), then fetch live data (slow)
        loadCache().then(() => {
            fetchLiveMetrics();
        });

        // Refresh live data every 5 minutes
        const interval = setInterval(fetchLiveMetrics, 5 * 60 * 1000);
        return () => clearInterval(interval);
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
