import { useState, useCallback } from 'preact/compat';
import { fetchWithRetry } from '../lib/fetchData';

interface SearchResult {
  identifier: string;
  tribunal: string;
  year: number;
  date?: string;
  item_size: number;
  files_count: number;
  downloads: number;
}

function formatBytes(bytes: number): string {
  if (bytes> 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (bytes> 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes> 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

function parseTribunalFromId(identifier: string): { tribunal: string; year: number } | null {
  const match = identifier.match(/^djen-(.+)-(\d{4})$/);
  if (!match) return null;
  return { tribunal: match[1].toUpperCase(), year: parseInt(match[2]) };
}

export function IASearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    const q = query.trim().toUpperCase();
    if (!q) return;

    setLoading(true);
    setSearched(true);

    try {
      // Build IA search query — search by tribunal code or date
      let iaQuery = '';
      let dateFilter: string | null = null;
      if (/^\d{4}$/.test(q)) {
        // Year search
        iaQuery = `identifier:djen-*-${q}`;
      } else if (/^\d{4}-\d{2}/.test(q)) {
        // Date or year-month search — query the year, then filter client-side
        const year = q.substring(0, 4);
        iaQuery = `identifier:djen-*-${year}`;
        // Use the original query as a date prefix filter (YYYY-MM or YYYY-MM-DD)
        dateFilter = query.trim();
      } else {
        // Tribunal code search
        iaQuery = `identifier:djen-${q.toLowerCase()}-*`;
      }

      const url = `https://archive.org/advancedsearch.php?q=${encodeURIComponent(iaQuery)}&fl[]=identifier&fl[]=item_size&fl[]=files_count&fl[]=downloads&fl[]=date&sort[]=downloads+desc&rows=100&output=json`;

      const res = await fetchWithRetry(url, {}, 3);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const docs = data?.response?.docs || [];

      let parsed: SearchResult[] = docs
        .map((doc: any) => {
          const info = parseTribunalFromId(doc.identifier);
          if (!info) return null;
          return {
            identifier: doc.identifier,
            tribunal: info.tribunal,
            year: info.year,
            date: doc.date,
            item_size: doc.item_size || 0,
            files_count: doc.files_count || 0,
            downloads: doc.downloads || 0,
          };
        })
        .filter(Boolean) as SearchResult[];

      // For month/date queries, filter to items whose date field matches the prefix
      if (dateFilter) {
        parsed = parsed.filter(r => r.date?.startsWith(dateFilter!));
      }

      setResults(parsed);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch();
  };

  return (
    <div className="mb-6">
      <div className="flex flex-col gap-3">
        <label className="input input-bordered flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4 opacity-70"><path fillRule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clipRule="evenodd" /></svg>
          <input
            id="ia-search-input"
            className="grow"
            type="search" value={query}
            onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar no Internet Archive (ex: TJSP, 2026, 2026-03)"
          />
          <kbd className="kbd kbd-sm hidden sm:inline-flex border-none shadow-none bg-base-200">Ctrl</kbd>
          <kbd className="kbd kbd-sm hidden sm:inline-flex border-none shadow-none bg-base-200">K</kbd>
        </label>
        
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <span className="text-sm font-semibold opacity-60 mr-1">Sugestões:</span>
          {['TJSP', 'TRF3', '2026', '2025', 'STJ'].map(tag => (
            <button key={tag} className="badge badge-outline hover:badge-primary cursor-pointer transition-colors px-3 py-3"
                onClick={() => {
                  setQuery(tag);
                  setTimeout(() => document.getElementById('search-submit-btn')?.click(), 50);
                }}>
              {tag}
            </button>
          ))}
          <button
            id="search-submit-btn"
            className="btn btn-primary btn-sm ml-auto px-6 hidden sm:flex"
            onClick={handleSearch} disabled={loading || !query.trim()}>
            {loading ? 'Buscando...' : 'Buscar'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="table-responsive opacity-50 mt-4 pointer-events-none">
          <table className="table table-zebra table-sm whitespace-nowrap">
            <thead>
              <tr>
                <th>Tribunal</th><th>Ano</th><th>Arquivos</th><th>Tamanho</th><th>Downloads</th><th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {[1, 2, 3].map(i => (
                <tr key={i} className="animate-pulse">
                  <td><div className="h-4 bg-base-300 rounded w-16"></div></td>
                  <td><div className="h-4 bg-base-300 rounded w-12"></div></td>
                  <td><div className="h-4 bg-base-300 rounded w-8"></div></td>
                  <td><div className="h-4 bg-base-300 rounded w-16"></div></td>
                  <td><div className="h-4 bg-base-300 rounded w-10"></div></td>
                  <td><div className="h-6 bg-base-300 rounded w-20"></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <p>Nenhum resultado encontrado.</p>
      )}

      {results.length> 0 && (
        <div>
          <div className="table-responsive">
            <table className="table table-zebra table-sm whitespace-nowrap">
              <thead>
              <tr>
                <th>Tribunal</th>
                <th>Ano</th>
                <th>Arquivos</th>
                <th>Tamanho</th>
                <th>Downloads</th>
                <th>Ação</th>
              </tr>
            </thead>
            <tbody>
              {results.map(r => {
                const isLarge = r.item_size > 1024 * 1024 * 1000; // > 1GB
                return (
                <tr key={r.identifier}>
                  <td className="font-bold">{r.tribunal}</td>
                  <td className="font-bold">{r.year}</td>
                  <td>{r.files_count}</td>
                  <td>
                    <span className={`badge ${isLarge ? 'badge-warning' : 'badge-ghost'} badge-sm`}>
                      {formatBytes(r.item_size)}
                    </span>
                  </td>
                  <td>{r.downloads > 0 ? r.downloads.toLocaleString() : '-'}</td>
                  <td>
                    <a
                      href={`https://archive.org/details/${r.identifier}`} target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-outline btn-xs no-animation flex-nowrap items-center gap-1 hover:bg-base-content hover:text-base-100">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                      </svg>
                      Ver no IA
                    </a>
                  </td>
                </tr>
                );
              })}
              </tbody>
            </table>
          </div>
          <small>{results.length} resultados</small>
        </div>
      )}
    </div>
  );
}
