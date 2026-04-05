import { useState, useEffect, useCallback } from 'preact/compat';
import { fetchAllTribunalMetadata, clearCache, getExpectedDays, TribunalMetadata } from '../lib/iaMetadataFetcher';
import { getCoverageColor } from '../lib/colorUtils';
import { isLeapYear } from '../lib/dateUtils';

const currentYear = new Date().getFullYear();
const YEARS = [currentYear - 2, currentYear - 1, currentYear];

export function AnnualCoverageMonitor() {
  const [year, setYear] = useState(currentYear);
  const [results, setResults] = useState<TribunalMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState('percentage');
  const [sortDir, setSortDir] = useState('desc');

  const fetchData = useCallback((forceRefresh: boolean = false) => {
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

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDir(field === 'tribunal' ? 'asc' : 'desc');
    }
  };

  const sorted: TribunalMetadata[] = [...results].sort((a, b) => {
    let cmp = 0;
    if (sortBy === 'tribunal') {
      cmp = a.tribunal.localeCompare(b.tribunal);
    } else if (sortBy === 'percentage') {
      cmp = a.percentage - b.percentage;
    } else if (sortBy === 'fileCount') {
      cmp = a.fileCount - b.fileCount;
    } else if (sortBy === 'downloads') {
      cmp = (a.downloads || 0) - (b.downloads || 0);
    }
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const expectedDays = getExpectedDays(year);
  const complete = results.filter(r => r.percentage>= 90).length;
  const partial = results.filter(r => r.percentage>= 50 && r.percentage < 90).length;
  const low = results.filter(r => r.percentage> 0 && r.percentage < 50).length;
  const missing = results.filter(r => r.percentage === 0).length;

  const sortIcon = (field: string): string => {
    if (sortBy !== field) return '';
    return sortDir === 'asc' ? ' \u2191' : ' \u2193';
  };

  return (
    <div>
      {/* Header */}
      <div>
        <h3>
          Cobertura Anual no Internet Archive
        </h3>
        <div>
          <div>
            {YEARS.map(y => (
              <button
                key={y} onClick={() => setYear(y)}
                className={year === y ? "btn" : "btn btn-secondary"}>
                {y}
              </button>
            ))}
          </div>
          <button
           onClick={() => fetchData(true)}
            disabled={loading}
            
            title="Atualizar dados">
            Refresh
          </button>
        </div>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div>
          Consultando Internet Archive...
        </div>
      )}

      {/* Summary cards */}
      {results.length> 0 && (
        <div className="grid">
          <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
            <div>{complete}</div>
            <small>{'>'}90%</small>
          </div></div>
          <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
            <div>{partial}</div>
            <small>50-89%</small>
          </div></div>
          <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
            <div>{low}</div>
            <small>{'<'}50%</small>
          </div></div>
          <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
            <div>{missing}</div>
            <small>Sem dados</small>
          </div></div>
        </div>
      )}

      {/* Expected days info */}
      <div>
        Esperado: {expectedDays} dias ({year === currentYear ? 'dias decorridos ate hoje' : `ano ${isLeapYear(year) ? 'bissexto' : 'normal'}`})
      </div>

      {/* Table */}
      <div>
        <div className="overflow-x-auto">
          <table className="table">
            <thead>
            <tr>
              <th
                
               onClick={() => handleSort('tribunal')}>
                Tribunal{sortIcon('tribunal')}
              </th>
              <th
                onClick={() => handleSort('fileCount')}>
                ZIPs{sortIcon('fileCount')}
              </th>
              <th>Esperado</th>
              <th
                onClick={() => handleSort('downloads')}>
                Downloads{sortIcon('downloads')}
              </th>
              <th
                onClick={() => handleSort('percentage')}>
                Cobertura{sortIcon('percentage')}
              </th>
              <th>Progresso</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(r => {
              const colors = getCoverageColor(r.percentage);
              const itemId = `djen-${r.tribunal.toLowerCase()}-${year}`;

              return (
                <tr
                  key={r.tribunal}>
                  <td>
                    <a
                      href={`https://archive.org/details/${itemId}`} target="_blank"
                      rel="noopener noreferrer">
                      {r.tribunal}
                    </a>
                  </td>
                  <td>
                    {r.fileCount}
                  </td>
                  <td>
                    {r.expectedDays}
                  </td>
                  <td>
                    {r.downloads> 0 ? r.downloads.toLocaleString() : '-'}
                  </td>
                  <td className={colors.text || undefined}>
                    {r.notFound ? 'N/A' : `${r.percentage.toFixed(1)}%`}
                    {r.error && !r.notFound && (
                      <span  title={r.error}>!</span>
                    )}
                  </td>
                  <td>
                    <div>
                      <div
                        className={colors.bg || undefined} style={{ width: `${Math.min(100, r.percentage)}%` }}
                      />
                    </div>
                  </td>
                </tr>
              );
            })}
            {results.length === 0 && !loading && (
              <tr>
                <td colSpan={6}>
                  Nenhum dado disponivel.
                </td>
              </tr>
            )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
