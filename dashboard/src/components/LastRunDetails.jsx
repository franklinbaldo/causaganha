import { ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';
import { SkeletonLoader, SkeletonText } from './SkeletonLoader';

export function LastRunDetails({ stats }) {
    const [expanded, setExpanded] = useState(true);

    if (!stats || !stats.steps) return (
        <div className="cyber-card">
            <div className="flex justify-between items-center mb-4">
                <SkeletonText width="w-48" height="h-6" />
                <SkeletonLoader className="w-5 h-5 rounded" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[...Array(4)].map((_, i) => (
                    <div key={i} className="bg-cyber-dark p-3 rounded border border-cyber-border">
                        <SkeletonText width="w-24" height="h-5" className="mb-4" />
                        <div className="space-y-2">
                            <SkeletonText width="w-full" height="h-3" />
                            <SkeletonText width="w-3/4" height="h-3" />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );

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
                        <div key={stepName} className="bg-cyber-dark p-3 rounded border border-cyber-border hover:border-cyber-primary transition-colors">
                            <div className="flex justify-between items-center mb-3 pb-2 border-b border-cyber-border">
                                <span className="font-bold text-cyber-text uppercase text-base">{stepName}</span>
                                <span className={clsx("text-xs px-2 py-0.5 rounded border font-bold",
                                    stepData.success !== 0 && stepData.failed === 0 ? "border-cyber-primary bg-cyber-secondary/10 text-cyber-primary" :
                                    stepData.success === true ? "border-cyber-primary bg-cyber-secondary/10 text-cyber-primary" :
                                    "border-cyber-danger bg-cyber-danger/10 text-cyber-danger"
                                )}>
                                    {stepData.success !== 0 && stepData.failed === 0 ? 'OK' : 'ATTENTION'}
                                </span>
                            </div>
                            <div className="space-y-1.5 text-sm text-cyber-gray font-mono">
                                {Object.entries(stepData).map(([k, v]) => {
                                    if (k === 'success') return null;
                                    return (
                                        <div key={k} className="flex justify-between items-baseline">
                                            <span className="truncate mr-2">{k.replace(/_/g, ' ')}</span>
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
