import { useState, useEffect } from 'react';
import { TRIBUNALS, LABELS } from '../lib/constants';
import { formatBytes } from '../lib/utils';
import { fetchDashboardCache, extractTribunalStatus } from '../lib/api';
import type { TribunalStatus } from '../lib/types';

const STATUS_COLORS = {
    ok: 'bg-accent-green text-white',
    absent: 'bg-accent-yellow/80 text-black',
    error: 'bg-accent-red text-white',
    pending: 'bg-text-muted/30 text-text-muted',
};

const STATUS_LABELS = {
    ok: LABELS.tribunals.status.ok,
    absent: LABELS.tribunals.status.absent,
    error: LABELS.tribunals.status.error,
    pending: LABELS.tribunals.status.pending,
};

interface TribunalData {
    status: Record<string, TribunalStatus>;
    date: string;
}

export default function TribunalHeatmap() {
    const [data, setData] = useState<TribunalData | null>(null);
    const [loading, setLoading] = useState(true);
    const [tooltip, setTooltip] = useState<{ x: number; y: number; tribunal: TribunalStatus } | null>(null);

    useEffect(() => {
        async function loadData() {
            const cache = await fetchDashboardCache();
            if (cache) {
                const { date, status } = extractTribunalStatus(cache);
                setData({ date, status });
            }
            setLoading(false);
        }
        loadData();
    }, []);

    const handleMouseEnter = (e: React.MouseEvent, tribunal: TribunalStatus) => {
        const rect = (e.target as HTMLElement).getBoundingClientRect();
        setTooltip({ x: rect.left + rect.width / 2, y: rect.top - 8, tribunal });
    };

    const renderGroup = (name: string, tribunals: readonly string[]) => (
        <div className="space-y-2">
            <h4 className="text-xs font-medium text-text-muted uppercase tracking-wide">{name}</h4>
            <div className="flex flex-wrap gap-1.5">
                {tribunals.map((code) => {
                    const status = data?.status[code] || { tribunal: code, status: 'pending' as const };
                    return (
                        <div
                            key={code}
                            onMouseEnter={(e) => handleMouseEnter(e, status)}
                            onMouseLeave={() => setTooltip(null)}
                            className={`
                px-2 py-1 rounded text-xs font-mono font-medium
                transition-all duration-150 cursor-default
                hover:scale-110 hover:shadow-lg
                ${STATUS_COLORS[status.status]}
              `}
                        >
                            {code}
                        </div>
                    );
                })}
            </div>
        </div>
    );

    if (loading) {
        return (
            <div className="space-y-6">
                {['Superiores', 'TRFs', 'TRTs', 'TJs'].map((group) => (
                    <div key={group} className="space-y-2">
                        <div className="skeleton h-4 w-32 rounded" />
                        <div className="flex flex-wrap gap-1.5">
                            {Array.from({ length: group === 'TJs' ? 27 : group === 'TRTs' ? 24 : 6 }).map((_, i) => (
                                <div key={i} className="skeleton h-6 w-12 rounded" />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Date header */}
            {data?.date && (
                <div className="text-sm text-text-muted">
                    Dados de <span className="font-mono text-text-primary">{data.date}</span>
                </div>
            )}

            {/* Tribunal groups */}
            {renderGroup(LABELS.tribunals.groups.superiores, TRIBUNALS.superiores)}
            {renderGroup(LABELS.tribunals.groups.trfs, TRIBUNALS.trfs)}
            {renderGroup(LABELS.tribunals.groups.trts, TRIBUNALS.trts)}
            {renderGroup(LABELS.tribunals.groups.tjs, TRIBUNALS.tjs)}

            {/* Legend */}
            <div className="flex flex-wrap gap-4 pt-4 border-t border-border text-xs text-text-muted">
                {Object.entries(STATUS_COLORS).map(([status, color]) => (
                    <div key={status} className="flex items-center gap-1.5">
                        <div className={`w-3 h-3 rounded ${color}`} />
                        <span>{STATUS_LABELS[status as keyof typeof STATUS_LABELS]}</span>
                    </div>
                ))}
            </div>

            {/* Tooltip */}
            {tooltip && (
                <div
                    className="fixed z-50 px-3 py-2 bg-page border border-border rounded-lg shadow-lg pointer-events-none animate-fade-in"
                    style={{
                        left: tooltip.x,
                        top: tooltip.y,
                        transform: 'translate(-50%, -100%)',
                    }}
                >
                    <div className="text-sm font-medium text-text-primary font-mono">{tooltip.tribunal.tribunal}</div>
                    <div className="text-xs text-text-muted">
                        {tooltip.tribunal.status === 'ok' && tooltip.tribunal.size
                            ? formatBytes(tooltip.tribunal.size)
                            : tooltip.tribunal.status === 'absent'
                                ? 'Sem publicação'
                                : tooltip.tribunal.status === 'error'
                                    ? 'Falha na coleta'
                                    : 'Pendente'}
                    </div>
                </div>
            )}
        </div>
    );
}
