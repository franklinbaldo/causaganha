import { useState, useEffect } from 'preact/compat';
import { getCoverageColorClass } from '../lib/colorUtils';

export function TribunalCoverageHeatmap() {
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize period from URL query param if available, defaulting to '90d'
  const [period, setPeriod] = useState(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlPeriod = params.get('period');
      if (['30d', '90d', '1a'].includes(urlPeriod ?? '')) {
        return urlPeriod!;
      }
    }
    return '90d';
  });

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
      } catch (e: unknown) {
        if (isMounted) {
          const message = e instanceof Error ? e.message : String(e);
          console.error('Failed to fetch catalog completed-items.json:', e);
          setError(message);
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

  const handlePeriodChange = (newPeriod: string) => {
    setPeriod(newPeriod);
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('period', newPeriod);
      window.history.replaceState({}, '', url.toString());
    }
  };

  const renderHeader = (title: string) => (
    <div>
      <h3>{title}</h3>
      <div>
        {['30d', '90d', '1a'].map(p => (
          <button
            key={p} onClick={() => handlePeriodChange(p)}
            className={`${
              period === p
                ? 'bg-white dark:bg-slate-600 shadow text-black dark:text-white font-medium'
                : 'text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white'
            }`}>
            {p}
          </button>
        ))}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="card">
        {renderHeader(`Recent Catalog Coverage (${period})`)}
        <div className="text-center">Loading coverage data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        {renderHeader(`Recent Catalog Coverage (${period})`)}
        <div className="text-center text-danger">Error: {error}</div>
      </div>
    );
  }

  const daysMap: Record<string, number> = {
    '30d': 30,
    '90d': 90,
    '1a': 365
  };
  const days = daysMap[period] || 90;

  // Get last N days sorted descending by date
  const sortedDates = Object.keys(data!).sort((a, b) => b.localeCompare(a));
  const recent = sortedDates.slice(0, days);

  return (
    <div className="card">
      {renderHeader(`Recent Catalog Coverage (${period})`)}
      <div>
        <table className="text-left">
          <thead>
            <tr>
              <th>Date</th>
              <th className="text-right">ZIPs Collected</th>
              <th className="text-right">Absent</th>
              <th className="text-right">Coverage %</th>
              <th>Visual Bar</th>
            </tr>
          </thead>
          <tbody>
            {recent.map(dateKey => {
              const item = data![dateKey];
              const tribunalCount = item.tribunal_count || 0;
              const absentCount = item.absent_count || 0;
              // Assuming 91 total Brazilian courts as context implies
              const total = tribunalCount + absentCount;
              // Coverage is based on successfully collected tribunals
              const pct = Math.min(100, (tribunalCount / 91) * 100);
              const displayDate = dateKey.replace('djen-', '');

              const colorClasses = getCoverageColorClass(pct);
              const textClass = colorClasses.split(' ')[0];
              const bgClass = colorClasses.split(' ')[1];

              return (
                <tr key={dateKey}>
                  <td>{displayDate}</td>
                  <td className="text-right">{tribunalCount}</td>
                  <td className="text-right">{absentCount}</td>
                  <td className={`text-right${total === 0 ? 'text-gray-400' : textClass}`}>
                    {pct.toFixed(1)}%
                  </td>
                  <td>
                    <div>
                      <div
                        className={`${total === 0 ? 'bg-gray-300 dark:bg-gray-600' : bgClass}`} style={{ width: `${Math.min(100, pct)}%` }}
                        title={`${pct.toFixed(1)}% Coverage`}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
            {recent.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center">No data available in catalog.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
