<script lang="ts">
  import {
    buildDailyStates,
    summarizeDailyStates,
    parseDrilldownQuery,
    buildDrilldownQuery,
  } from '../lib/tribunalCoverageDrilldown';
  import { loadTribunalCalendarPartition } from '../lib/tribunalCalendarPartition';

  interface Props {
    tribunals: string[];
    publicBase: string;
    initialTribunal: string;
    initialStart: string;
    initialEnd: string;
  }

  let { tribunals, publicBase, initialTribunal, initialStart, initialEnd }: Props = $props();

  const defaults = { tribunal: initialTribunal, start: initialStart, end: initialEnd };

  function readInitialState() {
    if (typeof window === 'undefined') return defaults;
    return parseDrilldownQuery(new URLSearchParams(window.location.search), tribunals, defaults);
  }

  const initial = readInitialState();
  let tribunal = $state(initial.tribunal);
  let start = $state(initial.start);
  let end = $state(initial.end);

  // Only the selected tribunal's partition is ever fetched (#1191) — never
  // the full tribunal_calendar contract, which client:only would otherwise
  // serialize whole into the page for every /stats visitor.
  let rows = $state<Awaited<ReturnType<typeof loadTribunalCalendarPartition>>>([]);
  let loadState = $state<'loading' | 'loaded' | 'error'>('loading');

  let dailyStates = $derived(buildDailyStates(rows ?? [], tribunal, start, end));
  let summary = $derived(summarizeDailyStates(dailyStates));

  const base = publicBase.endsWith('/') ? publicBase : publicBase + '/';
  let calendarHref = $derived(`${base}publicacoes/${tribunal.toLowerCase()}`);

  let requestSeq = 0;
  async function loadPartition(forTribunal: string) {
    const seq = ++requestSeq;
    loadState = 'loading';
    const result = await loadTribunalCalendarPartition(forTribunal, publicBase);
    if (seq !== requestSeq) return; // a newer tribunal was selected meanwhile — discard this response
    if (result === null) {
      rows = [];
      loadState = 'error';
      return;
    }
    rows = result;
    loadState = 'loaded';
  }

  $effect(() => {
    loadPartition(tribunal);
  });

  function syncUrl() {
    if (typeof window === 'undefined') return;
    const params = buildDrilldownQuery({ tribunal, start, end });
    const next = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, '', next);
  }

  function onTribunalChange(e: Event) {
    tribunal = (e.target as HTMLSelectElement).value;
    syncUrl();
  }

  function onStartChange(e: Event) {
    start = (e.target as HTMLInputElement).value;
    syncUrl();
  }

  function onEndChange(e: Event) {
    end = (e.target as HTMLInputElement).value;
    syncUrl();
  }
</script>

<div class="tribunal-explorer">
  <div class="tribunal-explorer__controls">
    <label class="tribunal-explorer__field">
      <span class="kicker">Tribunal</span>
      <select value={tribunal} onchange={onTribunalChange}>
        {#each tribunals as t}
          <option value={t}>{t}</option>
        {/each}
      </select>
    </label>

    <label class="tribunal-explorer__field">
      <span class="kicker">De</span>
      <input type="date" value={start} onchange={onStartChange} />
    </label>

    <label class="tribunal-explorer__field">
      <span class="kicker">Até</span>
      <input type="date" value={end} onchange={onEndChange} />
    </label>
  </div>

  <div aria-live="polite">
    {#if loadState === 'loading'}
      <p role="status" data-tone="muted">Carregando dados de {tribunal}…</p>
    {:else if loadState === 'error'}
      <p role="status" data-tone="attention">Não foi possível carregar os dados de {tribunal}. Tente novamente mais tarde.</p>
    {:else if summary.coveragePct === null}
      <p role="status" data-tone="muted">Sem evidência suficiente neste período para {tribunal}.</p>
    {:else}
      <p>
        {summary.uploaded} dia{summary.uploaded === 1 ? '' : 's'} preservado{summary.uploaded === 1 ? '' : 's'},
        {summary.absent} dia{summary.absent === 1 ? '' : 's'} com ausência confirmada
        ({summary.coveragePct}% de cobertura sobre os dias observados).
      </p>
      {#if summary.semEvidencia > 0}
        <small class="meta-text">{summary.semEvidencia} dia(s) do período sem evidência neste contrato.</small>
      {/if}
    {/if}
  </div>

  <a href={calendarHref}>Ver calendário completo de {tribunal} →</a>
</div>

<style>
  .tribunal-explorer {
    display: grid;
    gap: 1rem;
  }
  .tribunal-explorer__controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
    gap: 0.75rem;
  }
  .tribunal-explorer__field {
    display: grid;
    gap: 0.35rem;
  }
</style>
