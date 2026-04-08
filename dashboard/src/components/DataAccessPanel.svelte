<script lang="ts">
  import { onMount } from 'svelte';

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
        const res = await fetch(`https://archive.org/metadata/${itemId}/files`);
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
    class="btn btn-expand"
    onclick={() => (expanded = true)}>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
      <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6M12 9v6" />
    </svg>
    Acesso aos dados (DuckDB / Parquet)
  </button>
{:else}
  <div class="card"><div class="card-body">
    <header>
      <h4>Acesso aos Dados</h4>
      <button
        class="btn btn-outline"
        onclick={() => (expanded = false)}>
        Fechar
      </button>
    </header>

    <!-- DuckDB catalog query -->
    <section>
      <div>
        <span>Consulta via Catalogo (DuckDB)</span>
        <button
          class="btn btn-outline"
          onclick={() => copyToClipboard(catalogQuery, 'catalog')}>
          {copied === 'catalog' ? 'Copiado!' : 'Copiar'}
        </button>
      </div>
      <pre>{catalogQuery}</pre>
    </section>

    <!-- Parquet files -->
    {#if loading}
      <p aria-busy="true">Carregando arquivos...</p>
    {/if}

    {#if parquetFiles.length > 0}
      <section>
        <strong>
          Arquivos Parquet ({parquetFiles.length})
        </strong>
        <div>
          {#each parquetFiles as f (f.name)}
            <div>
              <div>
                <a
                  href={f.url} target="_blank"
                  rel="noopener noreferrer"
                  class="file-link">
                  {f.name}
                </a>
                <small>{formatSize(f.size)}</small>
              </div>
              <div>
                <code>
                  {duckdbQuery(f.name).substring(0, 80)}...
                </code>
                <button
                  class="btn btn-outline"
                  onclick={() => copyToClipboard(duckdbQuery(f.name), f.name)}>
                  {copied === f.name ? 'Copiado!' : 'SQL'}
                </button>
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    {#if !loading && parquetFiles.length === 0}
      <p>Nenhum arquivo Parquet encontrado neste item.</p>
    {/if}
  </div></div>
{/if}

<style>

  .btn-expand {
    width: 100%;
    background: var(--color-secondary, var(--color-primary));
    color: var(--color-secondary-content, var(--color-primary-content));
  }

  .btn-expand:hover {
    opacity: 0.9;
  }

  .btn-icon {
    width: 1.25rem;
    height: 1.25rem;
  }

  .file-link {
    color: var(--color-accent);
  }
</style>
