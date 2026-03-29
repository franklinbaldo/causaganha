import { useState, useEffect } from 'preact/compat';

export function TribunalCoverageHeatmap() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        setLoading(true);
        // Add cache-busting timestamp to always get the freshest catalog
        const response = await fetch(`https://archive.org/download/causaganha-catalog/completed-items.json?t=${Date.now()}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const json = await response.json();
        if (isMounted) {
          setData(json.completed_items || {});
          setError(null);
        }
      } catch (e) {
        if (isMounted) {
          console.error('Failed to fetch catalog completed-items.json:', e);
          setError(e.message);
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Recent Catalog Coverage (14 days)</h3>
        <div className="text-center text-gray-500 py-8">Loading coverage data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Recent Catalog Coverage (14 days)</h3>
        <div className="text-center text-danger py-8">Error: {error}</div>
      </div>
    );
  }

  // Get last 14 days sorted descending by date
  const sortedDates = Object.keys(data).sort((a, b) => b.localeCompare(a));
  const recent14 = sortedDates.slice(0, 14);

  const getCoverageColor = (pct) => {
    if (pct >= 80) return 'text-success bg-success'; // >80% Green
    if (pct >= 50) return 'text-warning bg-warning'; // 50-80% Yellow
    return 'text-danger bg-danger'; // <50% Red
  };

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-white">Recent Catalog Coverage (14 days)</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-800 text-sm text-gray-500 dark:text-gray-400">
              <th className="py-3 px-4 font-medium">Date</th>
              <th className="py-3 px-4 font-medium text-right">ZIPs Collected</th>
              <th className="py-3 px-4 font-medium text-right">Absent</th>
              <th className="py-3 px-4 font-medium text-right">Coverage %</th>
              <th className="py-3 px-4 font-medium w-1/3">Visual Bar</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {recent14.map(dateKey => {
              const item = data[dateKey];
              const tribunalCount = item.tribunal_count || 0;
              const absentCount = item.absent_count || 0;
              // Assuming 91 total Brazilian courts as context implies
              const total = tribunalCount + absentCount;
              // Coverage is based on successfully collected tribunals
              const pct = Math.min(100, (tribunalCount / 91) * 100);
              const displayDate = dateKey.replace('djen-', '');

              const colorClasses = getCoverageColor(pct);
              const textClass = colorClasses.split(' ')[0];
              const bgClass = colorClasses.split(' ')[1];

              return (
                <tr key={dateKey} className="border-b border-gray-100 dark:border-slate-800/50 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="py-3 px-4 text-black dark:text-white font-mono">{displayDate}</td>
                  <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{tribunalCount}</td>
                  <td className="py-3 px-4 text-right text-gray-500">{absentCount}</td>
                  <td className={`py-3 px-4 text-right font-semibold ${total === 0 ? 'text-gray-400' : textClass}`}>
                    {pct.toFixed(1)}%
                  </td>
                  <td className="py-3 px-4">
                    <div className="w-full h-2 bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
                      <div
                        className={`h-full ${total === 0 ? 'bg-gray-300 dark:bg-gray-600' : bgClass}`}
                        style={{ width: `${Math.min(100, pct)}%` }}
                        title={`${pct.toFixed(1)}% Coverage`}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
            {recent14.length === 0 && (
              <tr>
                <td colSpan="5" className="py-8 text-center text-gray-500">No data available in catalog.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
