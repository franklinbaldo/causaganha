import clsx from 'clsx';

export function CalendarHeatmap({ stats }) {
    // Generate dates for 2026
    const year = 2026;
    const today = stats?.current_date ? new Date(stats.current_date) : new Date();

    // Create matrix of days
    const days = [];
    const startDate = new Date(year, 0, 1);

    for (let i = 0; i < 365; i++) {
        const currentDate = new Date(startDate);
        currentDate.setDate(startDate.getDate() + i);

        let status = 'future';
        if (currentDate <= today) {
            // Pseudo-random deterministic status based on date hash for demo
            const hash = (currentDate.getDate() + currentDate.getMonth() * 31) % 10;
            if (hash > 3) status = 'full'; // 60% success
            else if (hash > 1) status = 'partial'; // 20% partial
            else status = 'empty'; // 20% empty

            // Force today to be successful if run was success
            if (currentDate.toDateString() === today.toDateString()) {
                status = stats?.status === 'success' ? 'full' : 'partial';
            }
        }

        days.push({ date: currentDate, status });
    }

    const months = Array.from({length: 12}, (_, i) => new Date(year, i, 1).toLocaleString('default', { month: 'short' }));

    return (
        <div className="cyber-card overflow-hidden">
             <h2 className="text-lg font-bold text-cyber-primary mb-4 flex justify-between items-center">
                <span>2026 Collection Status</span>
                <div className="flex gap-4 text-xs">
                    <span className="flex items-center gap-1"><div className="w-2 h-2 bg-cyber-primary rounded-sm"></div> Full</span>
                    <span className="flex items-center gap-1"><div className="w-2 h-2 bg-cyber-secondary opacity-60 rounded-sm"></div> Partial</span>
                    <span className="flex items-center gap-1"><div className="w-2 h-2 bg-cyber-danger opacity-40 rounded-sm"></div> Missing</span>
                </div>
             </h2>
             <div className="overflow-x-auto pb-2 custom-scrollbar">
                <div className="min-w-[800px]">
                    <div className="flex mb-2 pl-8">
                        {months.map((m, i) => (
                            <div key={i} className="flex-1 text-xs text-cyber-muted text-center">{m}</div>
                        ))}
                    </div>
                    <div className="flex">
                        <div className="flex flex-col justify-between text-[10px] text-cyber-muted pr-2 h-[100px] py-1">
                            <span>Mon</span>
                            <span>Wed</span>
                            <span>Fri</span>
                        </div>
                        <div className="grid grid-rows-7 grid-flow-col gap-[3px]">
                            {days.map((d, i) => (
                                <div
                                    key={i}
                                    className={clsx(
                                        "w-3 h-3 rounded-[1px] hover:ring-1 ring-white/80 transition-all cursor-pointer relative group",
                                        d.status === 'full' ? "bg-cyber-primary shadow-[0_0_2px_rgba(0,255,65,0.5)]" :
                                        d.status === 'partial' ? "bg-cyber-secondary opacity-60" :
                                        d.status === 'empty' ? "bg-cyber-danger opacity-40" :
                                        "bg-cyber-gray opacity-20"
                                    )}
                                >
                                   <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 hidden group-hover:block bg-cyber-black border border-cyber-border text-xs px-2 py-1 rounded whitespace-nowrap z-10 pointer-events-none">
                                     {d.date.toLocaleDateString()}
                                   </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
             </div>
        </div>
    );
}
