import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export function TimelineGraph({ data = [] }) {
    if (!data || data.length === 0) {
        return (
            <div className="cyber-card h-full min-h-[300px] flex flex-col items-center justify-center text-cyber-muted border-dashed">
                <p>Insufficient History</p>
            </div>
        )
    }

    // Format data for chart
    const chartData = data.map(d => ({
        date: d.date.split('-').slice(1).join('-'), // MM-DD
        uploads: d.count,
        fullDate: d.date
    }));

    return (
        <div className="cyber-card h-full min-h-[300px] flex flex-col" aria-label="Bar chart showing upload activity for the last 7 days">
             <h2 className="text-lg font-bold text-cyber-primary mb-4">Upload Activity (Last 7 Days)</h2>
             <div className="flex-1 w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis dataKey="date" stroke="#666" tick={{fill: '#888', fontSize: 10}} tickLine={false} axisLine={false} />
                        <YAxis stroke="#666" tick={{fill: '#888', fontSize: 10}} tickLine={false} axisLine={false} />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#0f0f0f', borderColor: '#333', color: '#e0e0e0' }}
                            itemStyle={{ color: '#00ff41' }}
                            cursor={{fill: 'rgba(0, 255, 65, 0.1)'}}
                            labelFormatter={(label, payload) => payload[0]?.payload.fullDate || label}
                        />
                        <Bar dataKey="uploads" fill="#008f11" radius={[2, 2, 0, 0]} animationDuration={1500} name="Uploads" />
                    </BarChart>
                </ResponsiveContainer>
             </div>
        </div>
    )
}
