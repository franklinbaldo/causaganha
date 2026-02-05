import clsx from 'clsx';

export function TribunalsGrid({ stats }) {
  const tribunals = stats?.tribunals || {};
  const items = Object.entries(tribunals).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div className="cyber-card">
      <h2 className="text-lg font-bold text-cyber-primary mb-4 flex items-center justify-between">
        <span>Tribunals Status</span>
        <span className="text-xs text-cyber-muted font-normal">{items.length} monitored</span>
      </h2>

      {items.length === 0 ? (
          <div className="text-cyber-muted text-sm italic py-8 text-center border border-dashed border-cyber-gray rounded bg-cyber-black/50">
              <p>No individual tribunal data available in this run.</p>
              <p className="text-xs mt-1 text-cyber-muted/50">Data is collected per run execution.</p>
          </div>
      ) : (
          <div role="list" className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-12 gap-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
            {items.map(([name, data]) => (
                <div
                    key={name}
                    className="flex flex-col items-center p-2 bg-cyber-dark border border-cyber-border hover:border-cyber-primary transition-colors rounded group cursor-help relative"
                    title={`Updated: ${data.last_update || 'N/A'}`}
                    role="listitem"
                >
                    <span className="font-bold text-xs text-cyber-text group-hover:text-cyber-primary">{name}</span>
                    <div className="flex items-center gap-1 mt-1">
                        <div
                            className={clsx("w-2.5 h-2.5 rounded-full",
                                data.status === 'success' ? "bg-cyber-primary shadow-glow" :
                                data.status === 'absent' ? "bg-cyber-muted" : "bg-cyber-danger shadow-glow-red"
                            )}
                            aria-hidden="true"
                        />
                        {/* Status symbols for color blindness */}
                        {data.status === 'success' && <span className="text-xs text-cyber-primary" aria-hidden="true">✓</span>}
                        {data.status === 'absent' && <span className="text-xs text-cyber-muted" aria-hidden="true">○</span>}
                        {(data.status !== 'success' && data.status !== 'absent') && <span className="text-xs text-cyber-danger" aria-hidden="true">✕</span>}
                    </div>
                    <span className="sr-only">
                        Status: {data.status === 'success' ? 'Online' : data.status === 'absent' ? 'Absent' : 'Error'}
                    </span>
                </div>
            ))}
          </div>
      )}
    </div>
  );
}
