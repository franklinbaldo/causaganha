import { useState, useEffect } from 'react';
import { API, TRIBUNALS, LABELS } from '../lib/constants';
import { formatBytes, getToday, getDaysAgo } from '../lib/utils';
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
        async function fetchData() {
            setLoading(true);

            // Try today first, then recent days
            for (let i = 0; i <= 5; i++) {
                const date = i === 0 ? getToday() : getDaysAgo(i);
                try {
                    const res = await fetch(API.IA_METADATA(date));
                    if (!res.ok) continue;

                    const metadata = await res.json();
                    if (!metadata.files || metadata.files.length === 0) continue;

                    const statusMap: Record<string, TribunalStatus> = {};

                    // Parse files
                    for (const file of metadata.files) {
                        const match = file.name.match(/djen-\d{4}-\d{2}-\d{2}-([A-Z0-9]+)\.(zip|absent)$/);
                        if (match) {
                            const tribunal = match[1];
                            const status = match[2] === 'zip' ? 'ok' : 'absent';
                            statusMap[tribunal] = {
                                tribunal,
                                status,
                                size: status === 'ok' ? parseInt(file.size, 10) : undefined,
                                fileCount: file.filecount ? parseInt(file.filecount, 10) : undefined,
                            };
                        }
                    }

                    // Mark missing tribunals as pending/error
                    const allTribunals = [
                        ...TRIBUNALS.superiores,
                        ...TRIBUNALS.trfs,
                        ...TRIBUNALS.trts,
                        ...TRIBUNALS.tjs,
                    ];

                    for (const tribunal of allTribunals) {
                        if (!statusMap[tribunal]) {
                            statusMap[tribunal] = {
                                tribunal,
                                status: i === 0 ? 'pending' : 'error', // pending for today, error for past
                            };
                        }
                    }

                    setData({ status: statusMap, date });
                    setLoading(false);
                    return;
                } catch {
                    continue;
                }
            }

            setLoading(false);
        }

        fetchData();
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
