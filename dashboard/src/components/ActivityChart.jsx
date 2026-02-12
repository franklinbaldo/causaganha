import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export function ActivityChart({ data = [] }) {
  if (!data || data.length === 0) {
    return (
      <div className="card h-full min-h-[280px] flex flex-col items-center justify-center text-content-tertiary">
        <p className="text-sm">No recent activity data</p>
      </div>
    );
  }

  const chartData = data.map(d => ({
    date: d.date.split('-').slice(1).join('/'),
    tribunals: d.count,
    fullDate: d.date,
  }));

  return (
    <div className="card h-full min-h-[280px] flex flex-col" aria-label="Bar chart showing daily collection volume">
      <h2 className="text-lg font-semibold text-content mb-4">Recent Activity</h2>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              stroke="var(--color-content-tertiary)"
              tick={{ fill: 'var(--color-content-secondary)', fontSize: 11, fontFamily: 'Inter' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="var(--color-content-tertiary)"
              tick={{ fill: 'var(--color-content-secondary)', fontSize: 11, fontFamily: '"JetBrains Mono"' }}
              tickLine={false}
              axisLine={false}
              domain={[0, 91]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-surface-raised)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-content)',
                borderRadius: '8px',
                fontSize: '13px',
                fontFamily: 'Inter',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              }}
              itemStyle={{ color: '#3b82f6' }}
              cursor={{ fill: 'rgba(59, 130, 246, 0.08)' }}
              labelFormatter={(label, payload) => payload[0]?.payload.fullDate || label}
            />
            <Bar
              dataKey="tribunals"
              fill="#3b82f6"
              radius={[4, 4, 0, 0]}
              animationDuration={800}
              name="Tribunals"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
