<script lang="ts">
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

  const suggestions = ['TJSP', 'TRF3', '2026', '2025', 'STJ'];

  let query = $state('');
  let results = $state<SearchResult[]>([]);
  let loading = $state(false);
  let searched = $state(false);

  let searchSubmitBtn: HTMLButtonElement;
  let suggestionTimeoutId: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    return () => {
      if (suggestionTimeoutId) clearTimeout(suggestionTimeoutId);
    };
  });

  async function handleSearch() {
    const q = query.trim().toUpperCase();
    if (!q) return;

    loading = true;
    searched = true;

    try {
      let iaQuery = '';
      let dateFilter: string | null = null;
      if (/^\d{4}$/.test(q)) {
        iaQuery = `identifier:djen-*-${q}`;
      } else if (/^\d{4}-\d{2}/.test(q)) {
        const year = q.substring(0, 4);
        iaQuery = `identifier:djen-*-${year}`;
        dateFilter = query.trim();
      } else {
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

      if (dateFilter) {
        parsed = parsed.filter(r => r.date?.startsWith(dateFilter!));
      }

      results = parsed;
    } catch {
      results = [];
    } finally {
      loading = false;
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'Enter') handleSearch();
  }
</script>

<div class="search-container">
  <div class="search-stack">
    <label class="search-input-wrapper">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="search-icon"><path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" /></svg>
      <input
        id="ia-search-input"
        class="search-input"
        type="search"
        value={query}
        oninput={(e) => query = (e.target as HTMLInputElement).value}
        onkeydown={handleKeyDown}
        placeholder="Buscar no Internet Archive (ex: TJSP, 2026, 2026-03)"
      />
      <kbd class="kbd-tag">Ctrl</kbd>
      <kbd class="kbd-tag">K</kbd>
    </label>

    <div class="suggestions-row">
      <span class="suggestions-label">Sugestões:</span>
      {#each suggestions as tag}
        <button class="suggestion-badge"
            onclick={() => {
              query = tag;
              if (suggestionTimeoutId) clearTimeout(suggestionTimeoutId);
              suggestionTimeoutId = setTimeout(() => {
                searchSubmitBtn?.click();
                suggestionTimeoutId = null;
              }, 50);
            }}>
          {tag}
        </button>
      {/each}
      <button
        bind:this={searchSubmitBtn}
        id="search-submit-btn"
        class="search-btn"
        onclick={handleSearch}
        disabled={loading || !query.trim()}>
        {#if loading}Buscando...{:else}Buscar{/if}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="table-responsive loading-overlay">
      <table class="data-table">
        <thead>
          <tr>
            <th>Tribunal</th><th>Ano</th><th>Arquivos</th><th>Tamanho</th><th>Downloads</th><th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {#each [1, 2, 3] as i}
            <tr class="skeleton-row">
              <td><div class="skeleton-block skeleton-w16"></div></td>
              <td><div class="skeleton-block skeleton-w12"></div></td>
              <td><div class="skeleton-block skeleton-w8"></div></td>
              <td><div class="skeleton-block skeleton-w16"></div></td>
              <td><div class="skeleton-block skeleton-w10"></div></td>
              <td><div class="skeleton-block skeleton-w20"></div></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if !loading && searched && results.length === 0}
    <p>Nenhum resultado encontrado.</p>
  {/if}

  {#if results.length > 0}
    <div>
      <div class="table-responsive">
        <table class="data-table">
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
            {#each results as r}
              {@const isLarge = r.item_size > 1024 * 1024 * 1000}
              <tr>
                <td class="cell-bold">{r.tribunal}</td>
                <td class="cell-bold">{r.year}</td>
                <td>{r.files_count}</td>
                <td>
                  <span class={`size-badge ${isLarge ? 'size-badge-warning' : 'size-badge-ghost'}`}>
                    {formatBytes(r.item_size)}
                  </span>
                </td>
                <td>{r.downloads > 0 ? r.downloads.toLocaleString() : '-'}</td>
                <td>
                  <a
                    href={`https://archive.org/details/${r.identifier}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="action-link">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="action-icon">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                    </svg>
                    Ver no IA
                  </a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <small>{results.length} resultados</small>
    </div>
  {/if}
</div>

<style>
  .search-container {
    margin-bottom: 1.5rem;
  }

  .search-stack {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .search-input-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-btn);
    padding: 0.5rem 0.75rem;
    background: var(--color-base-100);
  }

  .search-icon {
    width: 1rem;
    height: 1rem;
    opacity: 0.7;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    color: var(--color-base-content);
    font-size: var(--font-size-base);
  }

  .kbd-tag {
    display: none;
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    padding: 0.125rem 0.375rem;
    border-radius: var(--radius-btn);
    background: var(--color-base-200);
    border: none;
    box-shadow: none;
  }

  @media (min-width: 640px) {
    .kbd-tag {
      display: inline-flex;
    }
  }

  .suggestions-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .suggestions-label {
    font-size: var(--font-size-sm);
    font-weight: 600;
    opacity: 0.6;
    margin-right: 0.25rem;
  }

  .suggestion-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.375rem 0.75rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-full);
    background: transparent;
    color: var(--color-base-content);
    cursor: pointer;
    transition: var(--transition-base);
    font-size: var(--font-size-sm);
  }

  .suggestion-badge:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  .search-btn {
    display: none;
    margin-left: auto;
    padding: 0.375rem 1.5rem;
    background: var(--color-primary);
    color: var(--color-base-100);
    border: none;
    border-radius: var(--radius-btn);
    font-weight: 600;
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: var(--transition-base);
  }

  .search-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (min-width: 640px) {
    .search-btn {
      display: flex;
    }
  }

  .table-responsive {
    overflow-x: auto;
  }

  .loading-overlay {
    opacity: 0.5;
    margin-top: 1rem;
    pointer-events: none;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
    white-space: nowrap;
  }

  .data-table th,
  .data-table td {
    padding: 0.5rem 0.75rem;
    text-align: left;
  }

  .data-table thead th {
    font-weight: 600;
    border-bottom: 1px solid var(--color-base-300);
  }

  .data-table tbody tr:nth-child(even) {
    background: var(--color-base-200, rgba(0, 0, 0, 0.03));
  }

  .skeleton-row {
    animation: pulse 1.5s ease-in-out infinite;
  }

  .skeleton-block {
    height: 1rem;
    background: var(--color-base-300);
    border-radius: var(--radius-btn);
  }

  .skeleton-w8 { width: 2rem; }
  .skeleton-w10 { width: 2.5rem; }
  .skeleton-w12 { width: 3rem; }
  .skeleton-w16 { width: 4rem; }
  .skeleton-w20 { width: 5rem; }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .cell-bold {
    font-weight: 700;
  }

  .size-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
  }

  .size-badge-warning {
    background: color-mix(in srgb, var(--color-warning) 15%, transparent);
    color: var(--color-warning);
  }

  .size-badge-ghost {
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
  }

  .action-link {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    flex-wrap: nowrap;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-btn);
    color: var(--color-base-content);
    text-decoration: none;
    font-size: var(--font-size-xs);
    transition: var(--transition-base);
  }

  .action-link:hover {
    background: var(--color-base-content);
    color: var(--color-base-100);
  }

  .action-icon {
    width: 0.75rem;
    height: 0.75rem;
  }
</style>
