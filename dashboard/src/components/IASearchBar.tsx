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
  if (bytes > 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes > 1024) return `${(bytes / 1024).toFixed(0)} KB`;
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
    <div className="bg-white dark:bg-slate-900 rounded-xl border border-gray-200 dark:border-slate-800 p-4">
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={query}
          onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
          onKeyDown={handleKeyDown}
          placeholder="Buscar no Internet Archive (ex: TJSP, 2026, 2026-03)"
          className="flex-1 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-black dark:text-white placeholder-gray-400 focus:outline-none focus:border-accent"
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2 bg-accent text-white rounded-lg text-sm font-medium hover:bg-accent-light transition-colors disabled:opacity-50"
        >
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </div>

      {loading && (
        <div className="text-sm text-gray-500 py-4 text-center">Consultando Internet Archive...</div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-sm text-gray-500 py-4 text-center">Nenhum resultado encontrado.</div>
      )}

      {results.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-slate-800 text-gray-500 dark:text-gray-400">
                <th className="py-2 px-3 font-medium">Tribunal</th>
                <th className="py-2 px-3 font-medium text-right">Ano</th>
                <th className="py-2 px-3 font-medium text-right">Arquivos</th>
                <th className="py-2 px-3 font-medium text-right">Tamanho</th>
                <th className="py-2 px-3 font-medium text-right">Downloads</th>
                <th className="py-2 px-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {results.map(r => (
                <tr key={r.identifier} className="border-b border-gray-100 dark:border-slate-800/50 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
                  <td className="py-2 px-3 font-mono text-black dark:text-white">{r.tribunal}</td>
                  <td className="py-2 px-3 text-right text-gray-700 dark:text-gray-300">{r.year}</td>
                  <td className="py-2 px-3 text-right text-gray-700 dark:text-gray-300">{r.files_count}</td>
                  <td className="py-2 px-3 text-right text-gray-500">{formatBytes(r.item_size)}</td>
                  <td className="py-2 px-3 text-right text-gray-500">{r.downloads > 0 ? r.downloads.toLocaleString() : '-'}</td>
                  <td className="py-2 px-3 text-right">
                    <a
                      href={`https://archive.org/details/${r.identifier}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-accent hover:underline"
                    >
                      Ver no IA
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="text-xs text-gray-400 mt-2 text-right">{results.length} resultados</div>
        </div>
      )}
    </div>
  );
}
