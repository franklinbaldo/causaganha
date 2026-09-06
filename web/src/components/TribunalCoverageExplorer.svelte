<script lang="ts">
  import { onMount } from 'svelte';
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
  let copyStatus = $state('');

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

  function buildQueryHref(forTribunal = tribunal) {
    if (typeof window === 'undefined') return '#coverage-explorer';
    const params = buildDrilldownQuery({ tribunal: forTribunal, start, end });
    return `${window.location.pathname}?${params.toString()}#coverage-explorer`;
  }

  function syncUrl() {
    if (typeof window === 'undefined') return;
    const params = buildDrilldownQuery({ tribunal, start, end });
    const next = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, '', next);
    copyStatus = '';
  }

  function selectFromManifest(forTribunal: string) {
    tribunal = forTribunal;
    syncUrl();
    document.querySelector('#coverage-explorer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    window.setTimeout(() => {
      document.querySelector<HTMLSelectElement>('#coverage-explorer select')?.focus({ preventScroll: true });
    }, 350);
  }

  function refreshManifestLinks() {
    if (typeof document === 'undefined') return;
    for (const row of document.querySelectorAll<HTMLTableRowElement>('[data-tribunal-row]')) {
      const forTribunal = row.dataset.tribunal;
      const cell = row.querySelector<HTMLTableCellElement>('td:first-child');
      if (!forTribunal || !cell) continue;

      let link = cell.querySelector<HTMLAnchorElement>('[data-explore-tribunal]');
      if (!link) {
        link = document.createElement('a');
        link.dataset.exploreTribunal = '';
        link.className = 'manifest-explore-link';
        link.textContent = 'Explorar →';
        cell.append(document.createElement('br'), link);
        link.addEventListener('click', (event) => {
          event.preventDefault();
          const selected = link?.dataset.tribunal;
          if (selected) selectFromManifest(selected);
        });
      }

      link.dataset.tribunal = forTribunal;
      link.href = buildQueryHref(forTribunal);
      link.setAttribute('aria-label', `Explorar cobertura de ${forTribunal}`);
    }
  }

  onMount(() => {
    refreshManifestLinks();
  });

  $effect(() => {
    start;
    end;
    refreshManifestLinks();
  });

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

  function useRecentDays(days: number) {
    const parsedEnd = new Date(`${end}T00:00:00Z`);
    if (Number.isNaN(parsedEnd.getTime())) return;
    parsedEnd.setUTCDate(parsedEnd.getUTCDate() - (days - 1));
    start = parsedEnd.toISOString().slice(0, 10);
    syncUrl();
  }

  async function copyQueryLink() {
    if (typeof window === 'undefined') return;
    syncUrl();
    try {
      await navigator.clipboard.writeText(window.location.href);
      copyStatus = 'Link copiado.';
    } catch {
      copyStatus = 'Não foi possível copiar automaticamente. Copie o endereço do navegador.';
    }
  }
</script>

<div id="coverage-explorer" class="tribunal-explorer" tabindex="-1">
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

  <div class="tribunal-explorer__quick-ranges" role="group" aria-label="Períodos rápidos">
    <span class="kicker">Período rápido</span>
    <button type="button" onclick={() => useRecentDays(7)}>7 dias</button>
    <button type="button" onclick={() => useRecentDays(30)}>30 dias</button>
    <button type="button" onclick={() => useRecentDays(90)}>90 dias</button>
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

  <div class="tribunal-explorer__actions">
    <a href={calendarHref}>Ver calendário completo de {tribunal} →</a>
    <button type="button" class="tribunal-explorer__copy" onclick={copyQueryLink}>Copiar link desta consulta</button>
    <span class="meta-text" aria-live="polite">{copyStatus}</span>
  </div>
</div>

<style>
  .tribunal-explorer {
    display: grid;
    gap: 1rem;
    scroll-margin-top: 1rem;
  }
  .tribunal-explorer:focus {
    outline: none;
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
  .tribunal-explorer__quick-ranges,
  .tribunal-explorer__actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .tribunal-explorer__quick-ranges .kicker {
    margin-right: 0.25rem;
  }
  .tribunal-explorer__quick-ranges button,
  .tribunal-explorer__copy {
    min-height: 2.75rem;
    padding: 0.55rem 0.85rem;
    border: 1px solid currentColor;
    border-radius: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    font-weight: 700;
    cursor: pointer;
  }
  .tribunal-explorer__quick-ranges button:hover,
  .tribunal-explorer__quick-ranges button:focus-visible,
  .tribunal-explorer__copy:hover,
  .tribunal-explorer__copy:focus-visible {
    background: var(--colors-text, #171717);
    color: var(--colors-canvas, #fff);
  }
  .tribunal-explorer__actions .meta-text {
    flex-basis: 100%;
    min-height: 1.25rem;
  }
  :global(.manifest-explore-link) {
    display: inline-block;
    margin-top: 0.35rem;
    font-size: 0.8rem;
    font-weight: 700;
    white-space: nowrap;
  }
</style>