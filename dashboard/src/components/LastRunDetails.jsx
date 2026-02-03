import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

export function LastRunDetails({ stats }) {
    const [expanded, setExpanded] = useState(true);

    if (!stats || !stats.steps) return null;

    return (
        <div className="cyber-card">
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full flex justify-between items-center text-left hover:text-cyber-primary transition-colors"
            >
                <h2 className="text-lg font-bold text-cyber-primary">Last Run Details</h2>
                {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </button>

            <div className={clsx("transition-all duration-300 overflow-hidden", expanded ? "max-h-[1000px] mt-4 opacity-100" : "max-h-0 opacity-0")}>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {Object.entries(stats.steps).map(([stepName, stepData]) => (
                        <div key={stepName} className="bg-cyber-dark p-3 rounded border border-cyber-border hover:border-cyber-gray transition-colors">
                            <div className="flex justify-between items-center mb-3 pb-2 border-b border-cyber-gray">
                                <span className="font-bold text-cyber-text uppercase text-sm">{stepName}</span>
                                <span className={clsx("text-[10px] px-2 py-0.5 rounded border",
                                    stepData.success !== 0 && stepData.failed === 0 ? "border-cyber-primary bg-cyber-secondary/10 text-cyber-primary" :
                                    stepData.success === true ? "border-cyber-primary bg-cyber-secondary/10 text-cyber-primary" :
                                    "border-cyber-danger bg-cyber-danger/10 text-cyber-danger"
                                )}>
                                    {stepData.success !== 0 && stepData.failed === 0 ? 'OK' : 'ATTENTION'}
                                </span>
                            </div>
                            <div className="space-y-1.5 text-xs text-cyber-muted font-mono">
                                {Object.entries(stepData).map(([k, v]) => {
                                    if (k === 'success') return null;
                                    return (
                                        <div key={k} className="flex justify-between items-baseline">
                                            <span className="truncate mr-2 opacity-80">{k.replace(/_/g, ' ')}</span>
                                            <span className="text-cyber-text font-bold text-right">{v}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
