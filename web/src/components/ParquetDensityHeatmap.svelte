<script lang="ts">
  import { onMount } from 'svelte';
  import { getDuckDB } from '../lib/duckdbSingleton';
  import { fade } from 'svelte/transition';
  import CellTooltip from './CellTooltip.svelte';
  import MonthPicker from './MonthPicker.svelte';

  const MANIFEST_URL = 'https://ia600207.us.archive.org/29/items/causaganha-catalog/manifest.parquet';

  const STANDARD_TRIBUNALS = [
    'STF', 'STJ', 'TST', 'TSE', 'STM',
    'TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5', 'TRF6',
    'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDFT',
    'TJES', 'TJGO', 'TJMA', 'TJMG', 'TJMS', 'TJMT', 'TJPA',
    'TJPB', 'TJPE', 'TJPI', 'TJPR', 'TJRJ', 'TJRN', 'TJRO',
    'TJRR', 'TJRS', 'TJSC', 'TJSE', 'TJSP', 'TJMRS', 'TJMSP',
    'PJeCor',
  ];

  type Status = 'loading-db' | 'loading-data' | 'ready' | 'error';
  let status = $state<Status>('loading-db');
  let errorMsg = $state('');
  let conn = $state<any>(null);

  const _now = new Date();
  let selectedYear  = $state(_now.getUTCFullYear());
  let selectedMonth = $state(_now.getUTCMonth());

  let monthSummaries = $state<Record<string, number>>({});
  let data = $state<Record<string, Record<string, string>>>({});
  let displayDates = $state<string[]>([]);
  let tribunals = $state<string[]>([]);

  onMount(() => {
    let cancelled = false;

    async function initDB() {
      try {
        const { conn: connInstance } = await getDuckDB();

        if (!cancelled) {
          conn = connInstance;
          await Promise.all([fetchSummaries(connInstance), fetchMonthDetail(connInstance)]);
          if (!cancelled) status = 'ready';
        }
      } catch (err) {
        if (!cancelled) {
          status = 'error';
          errorMsg = err instanceof Error ? err.message : String(err);
        }
      }
    }

    initDB();
    return () => { cancelled = true; };
  });

  async function fetchSummaries(c: any) {
    const result = await c.query(`
      SELECT
        SUBSTR(date, 1, 7) AS month_key,
        COUNT(CASE WHEN file_type = 'parquet' THEN 1 END) * 1.0 /
          NULLIF(COUNT(DISTINCT date || '|' || tribunal), 0) AS pct
      FROM read_parquet('${MANIFEST_URL}')
      WHERE file_type IN ('zip', 'parquet')
      GROUP BY month_key
    `);
    const summaries: Record<string, number> = {};
    for (const row of result.toArray()) {
      const obj = row.toJSON();
      summaries[obj.month_key] = obj.pct ?? 0;
    }
    monthSummaries = summaries;
  }

  async function fetchMonthDetail(c?: any) {
    const connection = c ?? conn;
    if (!connection) return;
    status = 'loading-data';
    errorMsg = '';

    const mo   = String(selectedMonth + 1).padStart(2, '0');
    const from = `${selectedYear}-${mo}-01`;
    const nextMo = selectedMonth === 11
      ? `${selectedYear + 1}-01-01`
      : `${selectedYear}-${String(selectedMonth + 2).padStart(2, '0')}-01`;

    try {
      const result = await connection.query(`
        SELECT date, tribunal, file_type
        FROM read_parquet('${MANIFEST_URL}')
        WHERE date >= '${from}' AND date < '${nextMo}'
          AND file_type IN ('zip', 'parquet')
      `);

      const processData: Record<string, Record<string, string>> = {};
      const foundTribunals = new Set<string>();
      const foundDates     = new Set<string>();

      for (const row of result.toArray()) {
        const { date, tribunal, file_type } = row.toJSON();
        if (!processData[date]) processData[date] = {};
        foundTribunals.add(tribunal);
        foundDates.add(date);
        if (file_type === 'parquet') {
          processData[date][tribunal] = 'parquet';
        } else if (file_type === 'zip' && processData[date][tribunal] !== 'parquet') {
          processData[date][tribunal] = 'zip';
        }
      }

      data = processData;
      displayDates = Array.from(foundDates).sort((a, b) => b.localeCompare(a));
      const sorted = STANDARD_TRIBUNALS.filter(t => foundTribunals.has(t));
      foundTribunals.forEach(t => { if (!sorted.includes(t)) sorted.push(t); });
      tribunals = sorted.length > 0 ? sorted : STANDARD_TRIBUNALS;
      status = 'ready';
    } catch (err) {
      errorMsg = err instanceof Error ? err.message : String(err);
      status = 'error';
    }
  }

  // Re-query on month/year change (only after DuckDB is ready)
  $effect(() => {
    selectedYear; selectedMonth;
    if (conn) fetchMonthDetail();
  });

  function getCellStatus(dateStr: string, tribunal: string) {
    const s = data[dateStr]?.[tribunal];
    if (s === 'parquet') return 'parquet';
    if (s === 'zip')     return 'zip';
    return 'missing';
  }

  function getCellColor(s: string) {
    if (s === 'parquet') return 'bg-success';
    if (s === 'zip')     return 'bg-info';
    return 'bg-base-200';
  }
</script>

<div class="card bg-base-100 shadow-xl border border-base-200">
  <div class="card-body p-4 md:p-6">
    <div class="mb-4">
      <h2 class="card-title text-xl flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="text-primary" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        Densidade de Parquet
      </h2>
      <p class="text-sm text-base-content/70">Conversão de ZIPs para Parquet por tribunal.</p>
    </div>

    <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

    <div class="flex gap-4 text-xs font-medium mt-4 mb-2">
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-success inline-block"></span> Parquet</div>
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-info inline-block"></span> ZIP apenas</div>
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-base-200 inline-block"></span> Sem dados</div>
    </div>

    {#if status === 'loading-db' || status === 'loading-data'}
      <div class="flex justify-center items-center py-12">
        <span class="loading loading-spinner loading-lg text-primary" aria-busy="true"></span>
        <span class="ml-2 text-sm opacity-70">
          {status === 'loading-db' ? 'Carregando DuckDB...' : 'Consultando catálogo...'}
        </span>
      </div>
    {:else if status === 'error'}
      <div class="alert alert-error shadow-sm my-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Erro: {errorMsg}</span>
      </div>
    {:else}
      {#key `${selectedYear}-${selectedMonth}`}
        <div class="overflow-x-auto w-full pb-4" transition:fade={{ duration: 120 }}>
          <table class="table table-xs w-full min-w-max">
            <thead>
              <tr>
                <th class="sticky left-0 bg-base-100 z-10 opacity-70 w-24">Data</th>
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
                  <td class="sticky left-0 bg-base-100 z-10 font-mono text-[10px] whitespace-nowrap">{dateStr}</td>
                  {#each tribunals as tribunal}
                    {@const cellStatus = getCellStatus(dateStr, tribunal)}
                    <td class="p-0.5 min-w-[24px]">
                      <CellTooltip
                        cellData={{
                          date: dateStr,
                          status: cellStatus === 'parquet' ? 'Parquet' : cellStatus === 'zip' ? 'ZIP apenas' : 'missing',
                          uploadedAt: null,
                          sizeMb: null,
                        }}
                        position={{ x: 0, y: 0 }}
                      >
                        <div
                          class="w-6 h-6 rounded-sm mx-auto transition-all duration-200 hover:ring-2 hover:ring-primary/50 hover:scale-110 cursor-pointer {getCellColor(cellStatus)}"
                          role="button"
                          tabindex="0"
                          aria-label="{tribunal} em {dateStr}: {cellStatus}"
                        ></div>
                      </CellTooltip>
                    </td>
                  {/each}
                </tr>
              {/each}
              {#if displayDates.length === 0}
                <tr>
                  <td colspan={tribunals.length + 1} class="text-center py-4 opacity-50 text-sm">
                    Sem dados para este mês.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
        </div>
      {/key}
    {/if}
  </div>
</div>
