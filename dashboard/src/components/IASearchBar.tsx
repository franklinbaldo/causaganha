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
    <div>
      <div>
        <input
          type="search" value={query}
          onInput={(e) => setQuery((e.target as HTMLInputElement).value)}
          onKeyDown={handleKeyDown}
          placeholder="Buscar no Internet Archive (ex: TJSP, 2026, 2026-03)"
        />
        <button
          onClick={handleSearch} disabled={loading || !query.trim()}>
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </div>

      {loading && (
        <p aria-busy="true">Consultando Internet Archive...</p>
      )}

      {!loading && searched && results.length === 0 && (
        <p>Nenhum resultado encontrado.</p>
      )}

      {results.length> 0 && (
        <div>
          <table>
            <thead>
              <tr>
                <th>Tribunal</th>
                <th>Ano</th>
                <th>Arquivos</th>
                <th>Tamanho</th>
                <th>Downloads</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {results.map(r => (
                <tr key={r.identifier}>
                  <td>{r.tribunal}</td>
                  <td>{r.year}</td>
                  <td>{r.files_count}</td>
                  <td>{formatBytes(r.item_size)}</td>
                  <td>{r.downloads> 0 ? r.downloads.toLocaleString() : '-'}</td>
                  <td>
                    <a
                      href={`https://archive.org/details/${r.identifier}`} target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent">
                      Ver no IA
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <small>{results.length} resultados</small>
        </div>
      )}
    </div>
  );
}
