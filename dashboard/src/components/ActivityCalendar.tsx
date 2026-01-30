import { useState, useEffect, useMemo } from 'react';
import { LABELS, LINKS } from '../lib/constants';
import { formatBytes, formatDate, getCalendarLevel } from '../lib/utils';
import { fetchDashboardCache } from '../lib/api';

interface CalendarCell {
    date: string;
    level: 0 | 1 | 2 | 3 | 4;
    size: number;
    tribunalCount: number;
    isFuture: boolean;
}

interface YearStats {
    total: number;
    days: number;
    biggest: { date: string; size: number };
}

const LEVEL_COLORS = [
    'bg-border',
    'bg-accent-green/20',
    'bg-accent-green/40',
    'bg-accent-green/70',
    'bg-accent-green',
];

const DAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

// Start year for backfill tracking
const START_YEAR = 2021;

export default function ActivityCalendar() {
    const [calendarData, setCalendarData] = useState<Record<string, any>>({});
    const [loading, setLoading] = useState(true);
    const [tooltip, setTooltip] = useState<{ x: number; y: number; cell: CalendarCell } | null>(null);
    const [globalStats, setGlobalStats] = useState({ total: 0, days: 0, biggest: { date: '', size: 0 } });

    // Years to display (from START_YEAR to current year)
    const years = useMemo(() => {
        const currentYear = new Date().getFullYear();
        const result = [];
        for (let y = currentYear; y >= START_YEAR; y--) {
            result.push(y);
        }
        return result;
    }, []);

    // Load data from pre-built cache
    useEffect(() => {
        async function loadFromCache() {
            setLoading(true);
            const cache = await fetchDashboardCache();

            if (!cache) {
                setLoading(false);
                return;
            }

            setCalendarData(cache.calendar.days || {});

            // Calculate global stats
            const days = cache.calendar.days || {};
            const allDays = Object.entries(days).filter(([_, d]: [string, any]) => d.size > 0);
            const totalSize = allDays.reduce((acc, [_, d]: [string, any]) => acc + d.size, 0);
            const biggestDay = allDays.reduce((max, [date, d]: [string, any]) =>
                d.size > max.size ? { date, size: d.size } : max,
                { date: '', size: 0 }
            );

            setGlobalStats({
                total: totalSize,
                days: allDays.length,
                biggest: biggestDay,
            });
            setLoading(false);
        }

        loadFromCache();
    }, []);

    if (loading) {
        return (
            <div className="space-y-8 animate-pulse">
                {[1, 2, 3].map(i => (
                    <div key={i} className="h-24 bg-border/20 rounded-lg" />
                ))}
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Year grids */}
            {years.map(year => (
                <YearGrid
                    key={year}
                    year={year}
                    data={calendarData}
                    onTooltipShow={setTooltip}
                    onTooltipHide={() => setTooltip(null)}
                />
            ))}

            {/* Legend */}
            <div className="flex items-center justify-between text-xs text-text-muted pt-4 border-t border-border">
                <div className="flex items-center gap-2">
                    <span>{LABELS.activity.less}</span>
                    {LEVEL_COLORS.map((color, i) => (
                        <div key={i} className={`w-3 h-3 rounded-sm ${color}`} />
                    ))}
                    <span>{LABELS.activity.more}</span>
                </div>
            </div>

            {/* Global Stats */}
            <div className="flex flex-wrap gap-6 text-sm">
                <div>
                    <span className="text-text-muted">{LABELS.activity.total}: </span>
                    <span className="text-text-primary font-mono">{formatBytes(globalStats.total)}</span>
                </div>
                <div>
                    <span className="text-text-muted">{LABELS.activity.days}: </span>
                    <span className="text-text-primary font-mono">{globalStats.days}</span>
                </div>
                {globalStats.biggest.date && (
                    <div>
                        <span className="text-text-muted">{LABELS.activity.biggest}: </span>
                        <span className="text-text-primary font-mono">{globalStats.biggest.date}</span>
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

interface YearGridProps {
    year: number;
    data: Record<string, any>;
    onTooltipShow: (tooltip: { x: number; y: number; cell: CalendarCell }) => void;
    onTooltipHide: () => void;
}

function YearGrid({ year, data, onTooltipShow, onTooltipHide }: YearGridProps) {
    const today = formatDate(new Date());

    // Calculate max size for level scaling (within this year's data)
    const maxSize = useMemo(() => {
        const yearData = Object.entries(data)
            .filter(([date]) => date.startsWith(year.toString()))
            .map(([_, d]: [string, any]) => d.size || 0);
        return Math.max(...yearData, 1);
    }, [data, year]);

    // Generate weeks for the year
    const weeks = useMemo(() => {
        const result: CalendarCell[][] = [];
        const start = new Date(year, 0, 1);
        const end = new Date(year, 11, 31);

        // Adjust start to Monday
        const startDay = start.getDay();
        const diff = startDay === 0 ? 6 : startDay - 1;
        start.setDate(start.getDate() - diff);

        let current = new Date(start);
        while (current <= end || current.getDay() !== 1) {
            const week: CalendarCell[] = [];
            for (let i = 0; i < 7; i++) {
                const dateStr = formatDate(current);
                const dayData = data[dateStr];
                const isFuture = dateStr > today;
                const isThisYear = dateStr.startsWith(year.toString());
                const size = dayData?.size || 0;

                week.push({
                    date: dateStr,
                    level: isFuture || !isThisYear ? 0 : getCalendarLevel(size, maxSize),
                    size,
                    tribunalCount: dayData?.tribunal_count || 0,
                    isFuture: isFuture || !isThisYear,
                });
                current.setDate(current.getDate() + 1);
            }
            result.push(week);
            if (current > end && current.getDay() === 1) break;
        }
        return result;
    }, [year, data, today, maxSize]);

    // Month labels
    const monthLabels = useMemo(() => {
        const labels: { month: string; span: number }[] = [];
        let currentMonth = '';
        let span = 0;

        weeks.forEach((week) => {
            const firstDate = week[0]?.date;
            const date = new Date(firstDate);
            if (date.getFullYear() === year) {
                const month = date.toLocaleDateString('pt-BR', { month: 'short' });
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
    }, [weeks, year]);

    // Year stats
    const yearStats = useMemo(() => {
        const yearDays = Object.entries(data)
            .filter(([date, d]: [string, any]) => date.startsWith(year.toString()) && d.size > 0);
        const total = yearDays.reduce((acc, [_, d]: [string, any]) => acc + d.size, 0);
        return {
            days: yearDays.length,
            total,
        };
    }, [data, year]);

    const handleMouseEnter = (e: React.MouseEvent, cell: CalendarCell) => {
        if (cell.isFuture) return;
        const rect = (e.target as HTMLElement).getBoundingClientRect();
        onTooltipShow({ x: rect.left + rect.width / 2, y: rect.top - 8, cell });
    };

    const handleCellClick = (cell: CalendarCell) => {
        if (cell.size > 0) {
            window.open(LINKS.IA_DETAILS(cell.date), '_blank');
        }
    };

    return (
        <div className="space-y-2">
            {/* Year header with stats */}
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-text-primary">{year}</h3>
                <div className="text-xs text-text-muted">
                    <span className="font-mono text-text-primary">{yearStats.days}</span> dias •{' '}
                    <span className="font-mono text-text-primary">{formatBytes(yearStats.total)}</span>
                </div>
            </div>

            {/* Month labels */}
            <div className="flex pl-8 text-[10px] text-text-muted uppercase tracking-wider h-4">
                {monthLabels.map((label, i) => (
                    <div key={i} style={{ width: `${label.span * 14}px` }}>
                        {label.month}
                    </div>
                ))}
            </div>

            {/* Grid */}
            <div className="flex gap-1">
                {/* Day labels */}
                <div className="flex flex-col gap-[2px] text-[10px] text-text-muted w-6">
                    {DAY_LABELS.map((label, i) => (
                        <div key={i} className="h-[10px] flex items-center">{i % 2 === 0 ? label : ''}</div>
                    ))}
                </div>

                {/* Cells */}
                <div className="flex gap-[2px] overflow-x-auto pb-1 scrollbar-hide">
                    {weeks.map((week, wi) => (
                        <div key={wi} className="flex flex-col gap-[2px]">
                            {week.map((cell) => (
                                <div
                                    key={cell.date}
                                    onMouseEnter={(e) => handleMouseEnter(e, cell)}
                                    onMouseLeave={onTooltipHide}
                                    onClick={() => handleCellClick(cell)}
                                    className={`
                                        w-[10px] h-[10px] rounded-[2px] transition-all duration-100
                                        ${LEVEL_COLORS[cell.level]}
                                        ${cell.isFuture ? 'opacity-10' : ''}
                                        ${!cell.date.startsWith(year.toString()) ? 'opacity-0 pointer-events-none' : ''}
                                        ${cell.size > 0 ? 'cursor-pointer hover:ring-2 hover:ring-accent-green/50' : ''}
                                    `}
                                />
                            ))}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
