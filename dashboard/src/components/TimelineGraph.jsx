import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export function TimelineGraph({ stats }) {
    // Mock data for visualization since run-stats.json is single-run
    // In a real implementation, this should fetch a 'history.json' or derive from catalog data
    const data = [
        { date: '01-28', uploads: 65 },
        { date: '01-29', uploads: 50 },
        { date: '01-30', uploads: 80 },
        { date: '01-31', uploads: 45 },
        { date: '02-01', uploads: 90 },
        { date: '02-02', uploads: 120 },
        { date: '02-03', uploads: stats?.steps?.consolidate?.parquets_generated || 75 },
    ];

    return (
        <div className="cyber-card h-full min-h-[300px] flex flex-col">
             <h2 className="text-lg font-bold text-cyber-primary mb-4">Upload Activity (Last 7 Days)</h2>
             <div className="flex-1 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis dataKey="date" stroke="#666" tick={{fill: '#888', fontSize: 10}} tickLine={false} axisLine={false} />
                        <YAxis stroke="#666" tick={{fill: '#888', fontSize: 10}} tickLine={false} axisLine={false} />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0f0f0f', borderColor: '#333', color: '#e0e0e0' }}
                            itemStyle={{ color: '#00ff41' }}
                            cursor={{fill: 'rgba(0, 255, 65, 0.1)'}}
                        />
                        <Bar dataKey="uploads" fill="#008f11" radius={[2, 2, 0, 0]} animationDuration={1500} />
                    </BarChart>
                </ResponsiveContainer>
             </div>
        </div>
    )
}
