import clsx from 'clsx';

export function ActivityCalendar({ data = [] }) {
  const year = 2026;
  const today = new Date();

  const dataMap = new Map(data.map(d => [d.date, d.count]));

  const days = [];
  const startDate = new Date(year, 0, 1);

  for (let i = 0; i < 365; i++) {
    const currentDate = new Date(startDate);
    currentDate.setDate(startDate.getDate() + i);
    const dateStr = [
      currentDate.getFullYear(),
      String(currentDate.getMonth() + 1).padStart(2, '0'),
      String(currentDate.getDate()).padStart(2, '0')
    ].join('-');

    const count = dataMap.get(dateStr) || 0;
    let status = 'empty';

    if (currentDate > today) {
      status = 'future';
    } else if (count > 40) {
      status = 'full';
    } else if (count > 0) {
      status = 'partial';
    }

    days.push({ date: currentDate, status, count, dateStr });
  }

  const months = Array.from({ length: 12 }, (_, i) =>
    new Date(year, i, 1).toLocaleString('default', { month: 'short' })
  );

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-content">{year} Collection Activity</h2>
        <div className="flex items-center gap-3 text-xs text-content-tertiary">
          <span className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 bg-success rounded-sm" /> Full
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 bg-accent/60 rounded-sm" /> Partial
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 bg-danger/40 rounded-sm" /> Missing
          </span>
        </div>
      </div>

      <div className="overflow-x-auto pb-1">
        <div className="min-w-[800px]">
          {/* Month labels */}
          <div className="flex mb-1.5 pl-8">
            {months.map((m, i) => (
              <div key={i} className="flex-1 text-xs text-content-tertiary text-center font-medium">
                {m}
              </div>
            ))}
          </div>

          <div className="flex">
            {/* Day-of-week labels */}
            <div className="flex flex-col justify-between text-[10px] text-content-tertiary pr-2 h-[84px] py-0.5 font-medium">
              <span>Mon</span>
              <span>Wed</span>
              <span>Fri</span>
            </div>

            {/* Calendar grid */}
            <div className="grid grid-rows-7 grid-flow-col gap-[3px]">
              {days.map((d, i) => (
                <div
                  key={i}
                  role="gridcell"
                  aria-label={`${d.dateStr}: ${d.count} items`}
                  className={clsx(
                    "w-[11px] h-[11px] rounded-[2px] transition-all cursor-pointer relative group",
                    d.status === 'full' && "bg-success hover:ring-1 ring-success/60",
                    d.status === 'partial' && "bg-accent/60 hover:ring-1 ring-accent/40",
                    d.status === 'empty' && "bg-danger/40 hover:ring-1 ring-danger/30",
                    d.status === 'future' && "bg-surface-overlay"
                  )}
                >
                  {d.status !== 'future' && (
                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 hidden group-hover:block bg-surface-raised border border-border text-xs px-2 py-1 rounded-md shadow-elevated whitespace-nowrap z-10 pointer-events-none text-content">
                      <span className="font-medium">{d.dateStr}</span>
                      <span className="text-content-secondary ml-1">{d.count} items</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
