import { useState, useEffect } from 'react';
import { LABELS } from '../lib/constants';
import { formatBytes } from '../lib/utils';
import { fetchDashboardCache, getCacheAge } from '../lib/api';

interface PipelineMetrics {
    total_zips: number;
    days_consolidated: number;
    total_parquets: number;
    dates_collected: number;
    backfill_total: number;
    backfill_done: number;
    progress_pct: number;
}

interface MetricsData {
    filesToday: number;
    sizeToday: number;
    daysArchived: number;
    health: number;
    cacheAge?: string;
    source?: string;
    pipeline?: PipelineMetrics;
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
                    source: cache.meta.source,
                    pipeline: cache.today.pipeline,
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

    const p = data.pipeline;
    const pipelineMetrics = p ? [
        {
            title: LABELS.pipeline.zips.title,
            subtitle: LABELS.pipeline.zips.subtitle,
            value: p.total_zips.toLocaleString(),
            color: p.total_zips > 0 ? 'text-accent-green' : 'text-text-primary',
        },
        {
            title: LABELS.pipeline.consolidated.title,
            subtitle: LABELS.pipeline.consolidated.subtitle,
            value: p.days_consolidated,
            color: p.days_consolidated > 0 ? 'text-accent-green' : 'text-text-primary',
        },
        {
            title: LABELS.pipeline.progress.title,
            subtitle: `${p.backfill_done.toLocaleString()} / ${p.backfill_total.toLocaleString()}`,
            value: `${p.progress_pct}%`,
            color: p.progress_pct >= 50 ? 'text-accent-green' : p.progress_pct > 0 ? 'text-accent-yellow' : 'text-accent-red',
        },
    ] : [];

    return (
        <div className="space-y-4">
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
            {pipelineMetrics.length > 0 && (
                <>
                    <p className="text-xs font-medium uppercase tracking-wide text-text-muted px-1">
                        {LABELS.pipeline.title}
                    </p>
                    <div className="grid grid-cols-3 gap-4">
                        {pipelineMetrics.map((metric, i) => (
                            <div
                                key={`p-${i}`}
                                className="bg-card border border-border rounded-xl p-5 card-glow transition-all duration-200 hover:border-border-hover animate-slide-up"
                                style={{ animationDelay: `${(i + 4) * 50}ms` }}
                            >
                                <div className="space-y-1">
                                    <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                                        {metric.title}
                                    </p>
                                    <div className="h-9 flex items-baseline">
                                        {loading ? (
                                            <div className="skeleton h-7 w-16 rounded" />
                                        ) : (
                                            <p className={`text-2xl font-mono font-bold tabular-nums ${metric.color}`}>
                                                {metric.value}
                                            </p>
                                        )}
                                    </div>
                                    <p className="text-xs text-text-muted">
                                        {metric.subtitle}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
            {!loading && data.cacheAge && (
                <div className="text-xs text-text-muted text-right">
                    Atualizado {data.cacheAge}
                    {data.source && !data.source.includes('manifest') && (
                        <span className="ml-2 px-1.5 py-0.5 bg-accent-yellow/10 text-accent-yellow rounded">
                            dados parciais
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}
