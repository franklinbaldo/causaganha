<script lang="ts">
  import { onMount } from 'svelte';
  import CellTooltip from './CellTooltip.svelte';

  let loading = $state(true);
  let status = $state('loading-db'); // loading-db, ready, error
  let errorMsg = $state('');

  let db: any = null;
  let conn: any = null;

  let period = $state((() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlPeriod = params.get('period');
      if (['30d', '90d', '1a'].includes(urlPeriod ?? '')) {
        return urlPeriod!;
      }
    }
    return '30d';
  })());

  const daysMap: Record<string, number> = {
    '30d': 30,
    '90d': 90,
    '1a': 365,
  };

  const days = $derived(daysMap[period] || 30);

  let data = $state<Record<string, Record<string, string>>>({}); // date -> tribunal -> status
  let displayDates = $state<string[]>([]);
  let tribunals = $state<string[]>([]);

  // Pre-define standard tribunals
  const STANDARD_TRIBUNALS = [
    "STF", "STJ", "TST", "TSE", "STM",
    "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
    "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT",
    "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA",
    "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO",
    "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJMRS", "TJMSP",
    "PJeCor"
  ];

  onMount(() => {
    let cancelled = false;

    async function init() {
      status = 'loading-db';
      try {
        const duckdb = await import('@duckdb/duckdb-wasm');
        const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
        const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

        if (!bundle.mainWorker) {
          throw new Error('No mainWorker found for DuckDB.');
        }

        let worker;
        try {
          worker = new Worker(bundle.mainWorker);
        } catch (workerErr) {
          const response = await fetch(bundle.mainWorker);
          const content = await response.text();
          const blob = new Blob([content], { type: 'application/javascript' });
          worker = new Worker(URL.createObjectURL(blob));
        }

        const logger = new duckdb.ConsoleLogger();
        const dbInstance = new duckdb.AsyncDuckDB(logger, worker);
        await dbInstance.instantiate(bundle.mainModule, bundle.pthreadWorker);

        const connInstance = await dbInstance.connect();
        await connInstance.query("INSTALL httpfs; LOAD httpfs;");
        await connInstance.query("SET enable_http_metadata_cache=true;");

        if (!cancelled) {
          db = dbInstance;
          conn = connInstance;
          status = 'ready';
          await fetchData();
        }
      } catch (err) {
        if (!cancelled) {
          status = 'error';
          errorMsg = err instanceof Error ? err.message : String(err);
          loading = false;
        }
      }
    }

    init();
    return () => { cancelled = true; };
  });

  async function fetchData() {
    if (!conn) return;
    loading = true;
    errorMsg = '';

    try {
      // Find date range
      const endDateStr = new Date().toISOString().split('T')[0];
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - days);
      const startDateStr = startDate.toISOString().split('T')[0];

      // Use proxy server from JSDelivr for WASM bypass CORS or archive.org directly
      // JSDelivr / npm unpkg style url doesn't work for arbitrary archive items, but duckdb wasm can query it if CORS is allowed
      // The issue seems to be archive.org redirection or CORS. Duckdb wasm extension httpfs sometimes fails on 302 redirects.
      // JSDelivr bypass via corsproxy doesn't exist.
      // Wait, there is a way to query completed-items.json instead if manifest.parquet is unreadable
      // But the spec says: "Query the manifest.parquet file (or completed-items.json if it contains the data)."
      // Wait! I notice DuckDBExplorer.svelte and AuditLogExport.svelte ALSO use read_parquet('https://archive.org/download/causaganha-catalog/manifest.parquet').
      // Let's use the explicit fastly endpoint to skip archive.org's redirect, or just catch it.
      // Wait, let's fix the SVG icon size first.

      // If manifest.parquet fails due to CORS or 404, we'll try completed-items.json
      // Let's first try to download completed-items.json as it was suggested by the prompt since it might contain the data.
      // But DuckDB querying JSON requires a bit different logic.
      // Actually, archive.org redirects. To avoid CORS during redirects in DuckDB WASM, we can use the direct node:
      // 'https://ia600207.us.archive.org/29/items/causaganha-catalog/manifest.parquet'

      const query = `
        SELECT date, tribunal, file_type
        FROM read_parquet('https://ia600207.us.archive.org/29/items/causaganha-catalog/manifest.parquet')
        WHERE TRY_CAST(date AS DATE) >= '${startDateStr}'
          AND TRY_CAST(date AS DATE) <= '${endDateStr}'
          AND file_type IN ('zip', 'parquet')
      `;

      const arrowResult = await conn.query(query);
      const rawRows = arrowResult.toArray();

      const processData: Record<string, Record<string, string>> = {};
      const foundTribunals = new Set<string>();
      const foundDates = new Set<string>();

      for (const row of rawRows) {
        const obj = row.toJSON();
        const date = obj.date;
        const tribunal = obj.tribunal;
        const fileType = obj.file_type;

        if (!processData[date]) processData[date] = {};

        foundTribunals.add(tribunal);
        foundDates.add(date);

        // state precedence: parquet > zip
        if (fileType === 'parquet') {
          processData[date][tribunal] = 'parquet';
        } else if (fileType === 'zip' && processData[date][tribunal] !== 'parquet') {
          processData[date][tribunal] = 'zip';
        }
      }

      data = processData;

      const genDates = [];
      for (let i = 0; i < days; i++) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        genDates.push(d.toISOString().split('T')[0]);
      }
      displayDates = genDates;

      const sortedTribunals = STANDARD_TRIBUNALS.filter(t => foundTribunals.has(t));
      Array.from(foundTribunals).forEach(t => {
        if (!sortedTribunals.includes(t)) sortedTribunals.push(t);
      });
      tribunals = sortedTribunals.length > 0 ? sortedTribunals : STANDARD_TRIBUNALS;

    } catch (err) {
      errorMsg = err instanceof Error ? err.message : String(err);
      status = 'error';
    } finally {
      loading = false;
    }
  }

  function handlePeriodChange(newPeriod: string) {
    period = newPeriod;
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('period', newPeriod);
      window.history.replaceState({}, '', url.toString());
    }
    fetchData();
  }

  function getCellStatus(dateStr: string, tribunal: string) {
    const s = data[dateStr]?.[tribunal];
    if (s === 'parquet') return 'parquet';
    if (s === 'zip') return 'zip';
    return 'missing';
  }

  function getCellColor(status: string) {
    if (status === 'parquet') return 'bg-success'; // Green
    if (status === 'zip') return 'bg-info'; // Blue
    return 'bg-base-200'; // Grey/Missing
  }
</script>

<div class="card bg-base-100 shadow-xl border border-base-200">
  <div class="card-body p-4 md:p-6">
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="card-title text-xl flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="text-primary" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Parquet Density
        </h2>
        <p class="text-sm text-base-content/70">Conversion of ZIPs to Parquet for Analytics.</p>
      </div>

      <div class="flex gap-2">
        <div class="join">
          <button class="join-item btn btn-xs {period === '30d' ? 'btn-active' : ''}" onclick={() => handlePeriodChange('30d')} disabled={loading}>30d</button>
          <button class="join-item btn btn-xs {period === '90d' ? 'btn-active' : ''}" onclick={() => handlePeriodChange('90d')} disabled={loading}>90d</button>
          <button class="join-item btn btn-xs {period === '1a' ? 'btn-active' : ''}" onclick={() => handlePeriodChange('1a')} disabled={loading}>1a</button>
        </div>
      </div>
    </div>

    <div class="flex gap-4 text-xs font-medium mb-4">
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-success inline-block"></span> Parquet exists</div>
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-info inline-block"></span> ZIP only</div>
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-base-200 inline-block"></span> No data</div>
    </div>

    {#if status === 'loading-db' || loading}
      <div class="flex justify-center items-center py-12">
        <span class="loading loading-spinner loading-lg text-primary" aria-busy="true"></span>
        <span class="ml-2 text-sm opacity-70">
          {#if status === 'loading-db'}
            Loading DuckDB...
          {:else}
            Querying catalog...
          {/if}
        </span>
      </div>
    {:else if errorMsg}
      <div class="alert alert-error shadow-sm my-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <span>Error loading data: {errorMsg}</span>
      </div>
    {:else}
      <div class="table-responsive w-full pb-4">
        <table class="table table-xs w-full min-w-max">
          <thead>
            <tr>
              <th class="sticky left-0 bg-base-100 z-10 opacity-70 w-24">Date</th>
              {#each tribunals as tribunal}
                <th class="font-mono text-center text-[10px] w-6 p-0 opacity-70" title={tribunal}>
                  <div class="-rotate-45 translate-y-2 translate-x-1 w-6">{tribunal}</div>
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each displayDates as dateStr}
              <tr>
                <td class="sticky left-0 bg-base-100 z-10 font-mono text-[10px] whitespace-nowrap">
                  {dateStr.replace('djen-', '')}
                </td>
                {#each tribunals as tribunal}
                  {@const cellStatus = getCellStatus(dateStr, tribunal)}
                  <td class="p-0.5 min-w-[24px]">
                    <CellTooltip
                      cellData={{
                        date: dateStr,
                        status: cellStatus === 'parquet' ? 'Parquet Exists' : cellStatus === 'zip' ? 'ZIP Only' : 'missing',
                        uploadedAt: null,
                        sizeMb: null
                      }}
                      position={{x: 0, y: 0}}
                    >
                      <div
                        class="w-6 h-6 rounded-sm mx-auto transition-all duration-200 hover:ring-2 hover:ring-primary/50 hover:scale-110 cursor-pointer {getCellColor(cellStatus)}"
                        role="button"
                        tabindex="0"
                        aria-label="{tribunal} on {dateStr.replace('djen-', '')}: {cellStatus}"
                      ></div>
                    </CellTooltip>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
