import { useState, useEffect, useMemo } from 'react';
import { API, LABELS, CALENDAR_WEEKS } from '../lib/constants';
import { formatBytes, formatDate, getCalendarLevel, chunk } from '../lib/utils';
import type { DaySummary } from '../lib/types';

interface CalendarCell {
    date: string;
    level: 0 | 1 | 2 | 3 | 4;
    size: number;
    tribunalCount: number;
    isFuture: boolean;
}

const LEVEL_COLORS = [
    'bg-border',
    'bg-accent-green/20',
    'bg-accent-green/40',
    'bg-accent-green/70',
    'bg-accent-green',
];

const DAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

export default function ActivityCalendar() {
    const [cells, setCells] = useState<CalendarCell[]>([]);
    const [loading, setLoading] = useState(true);
    const [tooltip, setTooltip] = useState<{ x: number; y: number; cell: CalendarCell } | null>(null);
    const [stats, setStats] = useState({ total: 0, days: 0, biggest: { date: '', size: 0 } });

    // Generate dates for the calendar
    const dates = useMemo(() => {
        const result: string[] = [];
        const today = new Date();
        const totalDays = CALENDAR_WEEKS * 7;

        // Start from Monday, CALENDAR_WEEKS weeks ago
        const startDate = new Date(today);
        startDate.setDate(today.getDate() - totalDays + 1);
        const dayOfWeek = startDate.getDay();
        const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        startDate.setDate(startDate.getDate() - daysToMonday);

        for (let i = 0; i < totalDays; i++) {
            const date = new Date(startDate);
            date.setDate(startDate.getDate() + i);
            result.push(formatDate(date));
        }

        return result;
    }, []);

    // Fetch data for all dates
    useEffect(() => {
        async function fetchAllDates() {
            setLoading(true);
            const today = formatDate(new Date());
            const dataMap = new Map<string, { size: number; count: number }>();

            // Sample every 3rd day to reduce API calls, plus always include recent days
            const datesToFetch = dates.filter((date, i) => {
                const daysAgo = dates.length - 1 - i;
                return daysAgo <= 7 || i % 3 === 0;
            });

            // Fetch in parallel batches
            const batchSize = 5;
            for (let i = 0; i < datesToFetch.length; i += batchSize) {
                const batch = datesToFetch.slice(i, i + batchSize);
                const results = await Promise.all(
                    batch.map(async (date) => {
                        try {
                            const res = await fetch(API.IA_METADATA(date));
                            if (!res.ok) return { date, size: 0, count: 0 };
                            const data = await res.json();
                            const zipFiles = (data.files || []).filter((f: any) => f.name.endsWith('.zip'));
                            return { date, size: data.item_size || 0, count: zipFiles.length };
                        } catch {
                            return { date, size: 0, count: 0 };
                        }
                    })
                );
                results.forEach(r => dataMap.set(r.date, { size: r.size, count: r.count }));
            }

            // Calculate max size for level scaling
            const allSizes = Array.from(dataMap.values()).map(d => d.size);
            const maxSize = Math.max(...allSizes, 1);

            // Build cells
            const newCells: CalendarCell[] = dates.map(date => {
                const data = dataMap.get(date) || { size: 0, count: 0 };
                const isFuture = date > today;
                return {
                    date,
                    level: isFuture ? 0 : getCalendarLevel(data.size, maxSize),
                    size: data.size,
                    tribunalCount: data.count,
                    isFuture,
                };
            });

            // Calculate stats
            const daysWithData = newCells.filter(c => c.size > 0);
            const totalSize = daysWithData.reduce((acc, c) => acc + c.size, 0);
            const biggestDay = daysWithData.reduce((max, c) => c.size > max.size ? c : max, { date: '', size: 0 });

            setCells(newCells);
            setStats({
                total: totalSize,
                days: daysWithData.length,
                biggest: { date: biggestDay.date, size: biggestDay.size },
            });
            setLoading(false);
        }

        fetchAllDates();
    }, [dates]);

    // Group cells by week (columns)
    const weeks = useMemo(() => chunk(cells, 7), [cells]);

    // Get month labels for header
    const monthLabels = useMemo(() => {
        const labels: { month: string; span: number }[] = [];
        let currentMonth = '';
        let span = 0;

        weeks.forEach((week) => {
            const firstDate = week[0]?.date;
            if (firstDate) {
                const month = new Date(firstDate).toLocaleDateString('pt-BR', { month: 'short' });
                if (month !== currentMonth) {
                    if (currentMonth) labels.push({ month: currentMonth, span });
                    currentMonth = month;
                    span = 1;
                } else {
                    span++;
                }
            }
        });
        if (currentMonth) labels.push({ month: currentMonth, span });

        return labels;
    }, [weeks]);

    const handleCellClick = (cell: CalendarCell) => {
        if (cell.size > 0) {
            window.open(API.IA_DETAILS(cell.date), '_blank');
        }
    };

    const handleMouseEnter = (e: React.MouseEvent, cell: CalendarCell) => {
        if (cell.isFuture) return;
        const rect = (e.target as HTMLElement).getBoundingClientRect();
        setTooltip({ x: rect.left + rect.width / 2, y: rect.top - 8, cell });
    };

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="flex gap-1">
                    {Array.from({ length: 16 }).map((_, i) => (
                        <div key={i} className="flex flex-col gap-1">
                            {Array.from({ length: 7 }).map((_, j) => (
                                <div key={j} className="w-3 h-3 rounded-sm skeleton" />
                            ))}
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Month labels */}
            <div className="flex pl-8 text-xs text-text-muted">
                {monthLabels.map((label, i) => (
                    <div key={i} style={{ width: `${label.span * 16}px` }} className="capitalize">
                        {label.month}
                    </div>
                ))}
            </div>

            {/* Calendar grid */}
            <div className="flex gap-0">
                {/* Day labels */}
                <div className="flex flex-col gap-1 pr-2 text-xs text-text-muted">
                    {DAY_LABELS.map((label, i) => (
                        <div key={i} className="h-3 flex items-center">{i % 2 === 0 ? label : ''}</div>
                    ))}
                </div>

                {/* Cells */}
                <div className="flex gap-1 overflow-x-auto">
                    {weeks.map((week, wi) => (
                        <div key={wi} className="flex flex-col gap-1">
                            {week.map((cell) => (
                                <div
                                    key={cell.date}
                                    onClick={() => handleCellClick(cell)}
                                    onMouseEnter={(e) => handleMouseEnter(e, cell)}
                                    onMouseLeave={() => setTooltip(null)}
                                    className={`
                    w-3 h-3 rounded-sm transition-all duration-100
                    ${LEVEL_COLORS[cell.level]}
                    ${cell.isFuture ? 'opacity-30' : ''}
                    ${cell.size > 0 ? 'cursor-pointer hover:scale-150 hover:ring-2 hover:ring-accent-green/30' : ''}
                  `}
                                    title={cell.date}
                                />
                            ))}
                        </div>
                    ))}
                </div>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-between text-xs text-text-muted">
                <div className="flex items-center gap-2">
                    <span>{LABELS.activity.less}</span>
                    {LEVEL_COLORS.map((color, i) => (
                        <div key={i} className={`w-3 h-3 rounded-sm ${color}`} />
                    ))}
                    <span>{LABELS.activity.more}</span>
                </div>
            </div>

            {/* Stats */}
            <div className="flex flex-wrap gap-6 pt-4 border-t border-border text-sm">
                <div>
                    <span className="text-text-muted">{LABELS.activity.total}: </span>
                    <span className="text-text-primary font-mono">{formatBytes(stats.total)}</span>
                </div>
                <div>
                    <span className="text-text-muted">{LABELS.activity.days}: </span>
                    <span className="text-text-primary font-mono">{stats.days}</span>
                </div>
                {stats.biggest.date && (
                    <div>
                        <span className="text-text-muted">{LABELS.activity.biggest}: </span>
                        <span className="text-text-primary font-mono">{stats.biggest.date}</span>
                    </div>
                )}
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
                    <div className="text-sm font-medium text-text-primary">{tooltip.cell.date}</div>
                    <div className="text-xs text-text-muted">
                        {tooltip.cell.size > 0
                            ? `${formatBytes(tooltip.cell.size)} • ${tooltip.cell.tribunalCount} tribunais`
                            : 'Sem dados'}
                    </div>
                </div>
            )}
        </div>
    );
}
