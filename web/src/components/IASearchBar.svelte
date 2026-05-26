<script lang="ts">
  import { onMount } from 'svelte';
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
  let inputRef: HTMLInputElement | null = null;
  let shortcutEnabled = $state(false);
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

  function handleGlobalKeydown(e: KeyboardEvent) {
    if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== 'k') return;

    const commandPalette = document.getElementById('command-palette-dialog') as HTMLDialogElement | null;
    if (commandPalette?.open) return;

    e.preventDefault();
    (inputRef ?? document.getElementById('ia-search-input'))?.focus();
  }

  onMount(() => {
    shortcutEnabled = true;
    window.addEventListener('keydown', handleGlobalKeydown);
    return () => {
      shortcutEnabled = false;
      window.removeEventListener('keydown', handleGlobalKeydown);
    };
  });
</script>

<section>
  <search>
    <label>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" /></svg>
      <input
        id="ia-search-input"
        bind:this={inputRef}
        type="search"
        value={query}
        oninput={(e) => query = (e.target as HTMLInputElement).value}
        onkeydown={handleKeyDown}
        placeholder="Buscar no Internet Archive (ex: TJSP, 2026, 2026-03)"
        aria-label="Buscar no Internet Archive por tribunal ou ano"
        enterkeyhint="search"
      />
      {#if shortcutEnabled}
        <kbd>Ctrl</kbd>
        <kbd>K</kbd>
      {/if}
    </label>

    <div>
      <small>Sugestões:</small>
      {#each suggestions as tag}
        <button type="button" class="secondary outline"
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
        type="button"
        bind:this={searchSubmitBtn}
        id="search-submit-btn"
        onclick={handleSearch}
        disabled={loading || !query.trim()}
        aria-busy={loading}>
        {#if loading}Buscando...{:else}Buscar{/if}
      </button>
    </div>
  </search>

  {#if loading}
    <div class="table-responsive" aria-busy="true">
      <p role="status" class="sr-only">Carregando resultados da busca…</p>
      <table class="data-table" aria-hidden="true">
        <thead>
          <tr>
            <th>Tribunal</th><th>Ano</th><th>Arquivos</th><th>Tamanho</th><th>Downloads</th><th>Ação</th>
          </tr>
        </thead>
        <tbody>
          {#each [1, 2, 3] as i}
            <tr>
              <td colspan="6"><p aria-busy="true"></p></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if !loading && searched && results.length === 0}
    <p role="status">Nenhum resultado encontrado.</p>
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
                <td><strong>{r.tribunal}</strong></td>
                <td><strong>{r.year}</strong></td>
                <td>{r.files_count}</td>
                <td>
                  {#if isLarge}
                    <mark data-tone="warning">{formatBytes(r.item_size)}</mark>
                  {:else}
                    <small>{formatBytes(r.item_size)}</small>
                  {/if}
                </td>
                <td>{r.downloads > 0 ? r.downloads.toLocaleString('pt-BR') : '-'}</td>
                <td>
                  <a
                    href={`https://archive.org/details/${r.identifier}`}
                    target="_blank"
                    rel="noopener noreferrer">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
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
</section>
