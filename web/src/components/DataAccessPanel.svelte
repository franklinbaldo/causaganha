<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchWithRetry } from '../lib/fetchData';

  interface ParquetFile {
    name: string;
    size: number;
    url: string;
  }

  function formatSize(bytes: number): string {
    if (bytes > 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes > 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${bytes} B`;
  }

  interface DataAccessPanelProps {
    tribunalCode: string;
    year: number;
    snapshotParquetFiles?: { name: string; size: number }[];
  }

  let { tribunalCode, year, snapshotParquetFiles }: DataAccessPanelProps = $props();

  let parquetFiles: ParquetFile[] = $state([]);
  let loading = $state(false);
  let copied: string | null = $state(null);
  let expanded = $state(false);

  const itemId = $derived(`djen-${tribunalCode.toLowerCase()}-${year}`);
  const baseUrl = $derived(`https://archive.org/download/${itemId}`);

  const duckdbQuery = (fileName: string) =>
    `SELECT * FROM read_parquet('${baseUrl}/${fileName}') LIMIT 100;`;

  const catalogQuery = $derived(`-- Query all ${tribunalCode} data via the CausaGanha catalog
ATTACH 'https://archive.org/download/causaganha-catalog/catalog.duckdb' AS cg (READ_ONLY);
SELECT * FROM cg.comunicacoes WHERE tribunal = '${tribunalCode}' LIMIT 100;`);

  function copyToClipboard(text: string, label: string) {
    navigator.clipboard?.writeText(text);
    copied = label;
    setTimeout(() => (copied = null), 2000);
  }

  $effect(() => {
    if (snapshotParquetFiles && snapshotParquetFiles.length > 0) {
      parquetFiles = snapshotParquetFiles.map(f => ({
        ...f,
        url: `${baseUrl}/${f.name}`,
      }));
      return;
    }

    async function fetchFiles() {
      loading = true;
      try {
        const res = await fetchWithRetry(`https://archive.org/metadata/${itemId}/files`) as Response;
        if (!res.ok) return;
        const data = await res.json();
        const files = (data?.result || data || [])
          .filter((f: any) => f.name?.endsWith('.parquet'))
          .map((f: any) => ({
            name: f.name,
            size: parseInt(f.size) || 0,
            url: `${baseUrl}/${f.name}`,
          }));
        parquetFiles = files;
      } catch {
        // Silent fail
      } finally {
        loading = false;
      }
    }
    fetchFiles();
  });
</script>

{#if !expanded}
  <button
    type="button"
    class="expand-btn"
    onclick={() => (expanded = true)}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6M12 9v6" />
    </svg>
    Acesso aos dados (DuckDB / Parquet)
  </button>
{:else}
  <article>
    <header>
      <h4>Acesso aos Dados</h4>
      <button type="button" class="outline secondary" onclick={() => (expanded = false)}>Fechar</button>
    </header>

    <section>
      <div class="section-header">
        <span>Consulta via Catálogo (DuckDB)</span>
        <button type="button" class="outline secondary" onclick={() => copyToClipboard(catalogQuery, 'catalog')}>
          {copied === 'catalog' ? 'Copiado!' : 'Copiar'}
        </button>
      </div>
      <pre><code>{catalogQuery}</code></pre>
    </section>

    {#if loading}
      <p aria-live="polite" aria-busy="true">Carregando arquivos...</p>
    {/if}

    {#if parquetFiles.length > 0}
      <section>
        <strong>Arquivos Parquet ({parquetFiles.length})</strong>
        <ul class="file-list">
          {#each parquetFiles as f (f.name)}
            <li>
              <div class="file-row">
                <a href={f.url} target="_blank" rel="noopener noreferrer">{f.name}</a>
                <small>{formatSize(f.size)}</small>
              </div>
              <div class="query-row">
                <code>{duckdbQuery(f.name).substring(0, 80)}…</code>
                <button type="button" class="outline secondary" onclick={() => copyToClipboard(duckdbQuery(f.name), f.name)}>
                  {copied === f.name ? 'Copiado!' : 'SQL'}
                </button>
              </div>
            </li>
          {/each}
        </ul>
      </section>
    {/if}

    {#if !loading && parquetFiles.length === 0}
      <p>Nenhum arquivo Parquet encontrado neste item.</p>
    {/if}
  </article>
{/if}

<style>
  .expand-btn {
    width: 100%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: none;
    padding: 0;
    margin-bottom: 1rem;
  }

  header h4 { margin: 0; }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .file-list {
    list-style: none;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-top: 0.5rem;
  }

  .file-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .query-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }

  .query-row code {
    flex: 1;
    font-size: var(--font-size-xs);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
