import { useState, useEffect, useCallback } from 'preact/compat';
import { fetchAllTribunalMetadata, clearCache, getExpectedDays } from '../lib/iaMetadataFetcher.js';

const currentYear = new Date().getFullYear();
const YEARS = [currentYear - 2, currentYear - 1, currentYear];

function getCoverageColor(pct) {
  if (pct >= 90) return { text: 'text-green-600 dark:text-green-400', bg: 'bg-green-500' };
  if (pct >= 50) return { text: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-500' };
  if (pct > 0) return { text: 'text-red-600 dark:text-red-400', bg: 'bg-red-500' };
  return { text: 'text-gray-400 dark:text-gray-500', bg: 'bg-gray-300 dark:bg-gray-600' };
}

export function AnnualCoverageMonitor() {
  const [year, setYear] = useState(currentYear);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState('percentage');
  const [sortDir, setSortDir] = useState('desc');

  const fetchData = useCallback((forceRefresh = false) => {
    setLoading(true);

    if (forceRefresh) clearCache(year);

    fetchAllTribunalMetadata(year, (_done, _total, partial) => {
      setResults([...partial]);
    }, { useCache: !forceRefresh }).then((final) => {
      setResults(final);
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });
  }, [year]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDir(field === 'tribunal' ? 'asc' : 'desc');
    }
  };

  const sorted = [...results].sort((a, b) => {
    let cmp = 0;
    if (sortBy === 'tribunal') {
      cmp = a.tribunal.localeCompare(b.tribunal);
    } else if (sortBy === 'percentage') {
      cmp = a.percentage - b.percentage;
    } else if (sortBy === 'fileCount') {
      cmp = a.fileCount - b.fileCount;
    }
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const expectedDays = getExpectedDays(year);
  const complete = results.filter(r => r.percentage >= 90).length;
  const partial = results.filter(r => r.percentage >= 50 && r.percentage < 90).length;
  const low = results.filter(r => r.percentage > 0 && r.percentage < 50).length;
  const missing = results.filter(r => r.percentage === 0).length;

  const sortIcon = (field) => {
    if (sortBy !== field) return '';
    return sortDir === 'asc' ? ' \u2191' : ' \u2193';
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-center mb-4 gap-3">
        <h3 className="text-lg font-semibold text-black dark:text-white">
          Cobertura Anual no Internet Archive
        </h3>
        <div className="flex items-center gap-3">
          <div className="flex bg-gray-100 dark:bg-slate-800 p-1 rounded-lg">
            {YEARS.map(y => (
              <button
                key={y}
                onClick={() => setYear(y)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  year === y
                    ? 'bg-white dark:bg-slate-600 shadow text-black dark:text-white font-medium'
                    : 'text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white'
                }`}
              >
                {y}
              </button>
            ))}
          </div>
          <button
            onClick={() => fetchData(true)}
            disabled={loading}
            className="px-3 py-1 text-sm rounded-md bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-400 hover:text-black dark:hover:text-white transition-colors disabled:opacity-50"
            title="Atualizar dados"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="mb-4 text-sm text-gray-500 dark:text-gray-400">
          Consultando Internet Archive...
        </div>
      )}

      {/* Summary cards */}
      {results.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">{complete}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{'>'}90%</div>
          </div>
          <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{partial}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">50-89%</div>
          </div>
          <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">{low}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{'<'}50%</div>
          </div>
          <div className="bg-gray-50 dark:bg-slate-800 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-gray-500 dark:text-gray-400">{missing}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">Sem dados</div>
          </div>
        </div>
      )}

      {/* Expected days info */}
      <div className="text-xs text-gray-400 dark:text-gray-500 mb-3">
        Esperado: {expectedDays} dias ({year === currentYear ? 'dias decorridos ate hoje' : `ano ${isLeapYear(year) ? 'bissexto' : 'normal'}`})
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[600px]">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-800 text-sm text-gray-500 dark:text-gray-400">
              <th
                className="py-3 px-4 font-medium cursor-pointer hover:text-black dark:hover:text-white select-none"
                onClick={() => handleSort('tribunal')}
              >
                Tribunal{sortIcon('tribunal')}
              </th>
              <th
                className="py-3 px-4 font-medium text-right cursor-pointer hover:text-black dark:hover:text-white select-none"
                onClick={() => handleSort('fileCount')}
              >
                ZIPs{sortIcon('fileCount')}
              </th>
              <th className="py-3 px-4 font-medium text-right">Esperado</th>
              <th
                className="py-3 px-4 font-medium text-right cursor-pointer hover:text-black dark:hover:text-white select-none"
                onClick={() => handleSort('percentage')}
              >
                Cobertura{sortIcon('percentage')}
              </th>
              <th className="py-3 px-4 font-medium w-1/3">Progresso</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {sorted.map(r => {
              const colors = getCoverageColor(r.percentage);
              const itemId = `djen-${r.tribunal.toLowerCase()}-${year}`;

              return (
                <tr
                  key={r.tribunal}
                  className="border-b border-gray-100 dark:border-slate-800/50 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-black dark:text-white">
                    <a
                      href={`https://archive.org/details/${itemId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="hover:underline hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {r.tribunal}
                    </a>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">
                    {r.fileCount}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-500">
                    {r.expectedDays}
                  </td>
                  <td className={`py-3 px-4 text-right font-semibold ${colors.text}`}>
                    {r.notFound ? 'N/A' : `${r.percentage.toFixed(1)}%`}
                    {r.error && !r.notFound && (
                      <span className="ml-1 text-xs text-red-400" title={r.error}>!</span>
                    )}
                  </td>
                  <td className="py-3 px-4">
                    <div className="w-full h-2 bg-gray-100 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${colors.bg} transition-all duration-300`}
                        style={{ width: `${Math.min(100, r.percentage)}%` }}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
            {results.length === 0 && !loading && (
              <tr>
                <td colSpan="5" className="py-8 text-center text-gray-500">
                  Nenhum dado disponivel.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function isLeapYear(year) {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}
