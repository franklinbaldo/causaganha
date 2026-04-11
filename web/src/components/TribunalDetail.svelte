<script lang="ts">
  import { onMount } from 'svelte';
  import { TRIBUNAIS, TRIBUNAL_GROUPS } from '../lib/tribunais';
  import { useDashboardWithPolling } from '../lib/useDashboard.svelte';
  import QueryProvider from './QueryProvider.svelte';
  import { toDateString } from '../lib/dateUtils';
  import Heatmap from './Heatmap.svelte';
  import { calculateVelocityAndRegression } from '../lib/velocityCalc';
  import DateDetail from './DateDetail.svelte';
  import DataAccessPanel from './DataAccessPanel.svelte';

  interface HashState {
    date: string | null;
    page: number | null;
    seq: number | null;
  }

  function parseHash(): HashState {
    if (typeof window === 'undefined') return { date: null, page: null, seq: null };
    const hash = window.location.hash.replace(/^#/, '');
    if (!hash) return { date: null, page: null, seq: null };
    const parts = hash.split('/');
    const date = parts[0] || null;
    let page: number | null = null;
    let seq: number | null = null;
    // Named keys: #date/pg/2/seq/1050
    for (let i = 1; i + 1 < parts.length; i += 2) {
      if (parts[i] === 'pg')  page = parseInt(parts[i + 1]);
      if (parts[i] === 'seq') seq  = parseInt(parts[i + 1]);
    }
    // Positional fallback for old links: #date/N or #date/N/M
    if (page === null && parts[1] && /^\d+$/.test(parts[1])) page = parseInt(parts[1]);
    if (seq  === null && parts[2] && /^\d+$/.test(parts[2])) seq  = parseInt(parts[2]);
    return { date, page, seq };
  }

  interface TribunalDetailProps {
    tribunalCode: string;
    initialCoverage: Record<string, string[]> | null;
    initialEtas: Record<string, any> | null;
    initialTargetRange: { start: string; end: string } | null;
    initialStartDates: Record<string, string> | null;
    initialQualityScores: Record<string, any> | null;
  }

  let {
    tribunalCode,
    initialCoverage,
    initialEtas,
    initialTargetRange,
    initialStartDates,
    initialQualityScores,
  }: TribunalDetailProps = $props();

  const dashboard = useDashboardWithPolling();

  let selectedTribunal = $state(tribunalCode.toUpperCase());
  let hashState = $state<HashState>({ date: null, page: null, seq: null });
  let hashReady = $state(false);

  onMount(() => {
    hashState = parseHash();
    hashReady = true;
    const onNavigate = () => { hashState = parseHash(); };
    window.addEventListener('hashchange', onNavigate);
    window.addEventListener('popstate', onNavigate);
    return () => {
      window.removeEventListener('hashchange', onNavigate);
      window.removeEventListener('popstate', onNavigate);
    };
  });

  let allData = $derived(dashboard.data);

  let coverage = $derived(allData?.tribunalCoverage ?? initialCoverage ?? {});
  let absentCoverage = $derived(allData?.tribunalAbsentCoverage ?? {});
  let etas = $derived(allData?.tribunalEtas ?? initialEtas ?? {});
  let startDates = $derived(allData?.tribunalStartDates ?? initialStartDates ?? {});
  let qualityScores = $derived(allData?.tribunalQualityScores ?? initialQualityScores ?? {});
  let iaSnapshot = $derived(allData?.iaSnapshot);

  let activeDate = $derived.by(() => {
    let date = hashState.date;
    if (!date && iaSnapshot?.items) {
      for (const item of Object.values(iaSnapshot.items)) {
        if (item.tribunal === selectedTribunal) {
          if (!date || item.latest_date > date) {
            date = item.latest_date;
          }
        }
      }
    }
    return date;
  });

  let backfillTargetRange = $derived(allData?.targetRange ?? initialTargetRange);
  let today = $derived(toDateString(new Date()));
  let targetRange = $derived({
    start: backfillTargetRange?.start || "2024-01-01",
    end: backfillTargetRange?.end || today,
  });

  const BASE = import.meta.env.BASE_URL;
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  function handleTribunalChange(e: Event) {
    const newTribunal = (e.target as HTMLSelectElement).value;
    if (!TRIBUNAIS.includes(newTribunal)) return;
    selectedTribunal = newTribunal;
    window.location.href = `${baseUrl}publicacoes/${encodeURIComponent(newTribunal.toLowerCase())}`;
  }

  let snapshotDates = $derived.by(() => {
    const dates = new Set<string>();
    if (iaSnapshot?.items) {
      for (const item of Object.values(iaSnapshot.items)) {
        if (item.tribunal === selectedTribunal) {
          item.dates.forEach((d: string) => dates.add(d));
        }
      }
    }
    return dates;
  });

  let selectedCoverage = $derived(snapshotDates.size > 0 ? snapshotDates : new Set(coverage[selectedTribunal] || []));
  let selectedEtaData = $derived(etas[selectedTribunal] || { missing_days: null, velocity_14d: 0, eta_days: null });
  let tribunalStartDate = $derived(startDates[selectedTribunal] || selectedEtaData.genesis_date);

  let expectedDays = $derived.by(() => {
    if (!tribunalStartDate) return 0;
    const start = new Date(tribunalStartDate + "T00:00:00Z");
    const end = new Date(targetRange.end + "T00:00:00Z");
    if (start <= end) {
      return Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    }
    return 0;
  });

  let actualMissingDays = $derived(
    selectedEtaData.missing_days !== null
      ? selectedEtaData.missing_days
      : Math.max(0, expectedDays - selectedCoverage.size)
  );

  let isStopped = $derived(selectedEtaData.stopped || false);
  let cursorDate = $derived(selectedEtaData.cursor_date);
  let completionPct = $derived(selectedEtaData.completion_pct || 0);
  let genesisDate = $derived(selectedEtaData.genesis_date || tribunalStartDate);

  let velocityMetrics = $derived(calculateVelocityAndRegression(selectedCoverage, targetRange.end, tribunalStartDate));

  let dynamicEtaDays = $derived.by(() => {
    let eta = selectedEtaData.eta_days;
    if (velocityMetrics && velocityMetrics.currentVelocity > 0 && actualMissingDays > 0) {
      eta = Math.ceil(actualMissingDays / (velocityMetrics.currentVelocity / 7));
    }
    return eta;
  });

  let etaText = $derived.by(() => {
    if (actualMissingDays === 0 && expectedDays > 0) return "Concluido";
    if (dynamicEtaDays) {
      if (dynamicEtaDays < 30) return `~${dynamicEtaDays} dias`;
      const months = Math.round(dynamicEtaDays / 30);
      return `~${months} ${months > 1 ? 'meses' : 'mes'}`;
    }
    return "Pendente";
  });

  let isComplete = $derived(actualMissingDays === 0 && expectedDays > 0);
  let statusColor = $derived(isComplete ? "value-success" : "value-warning");

  let absentList = $derived(absentCoverage[selectedTribunal] || []);
  let absentSet = $derived(new Set(absentList));

  let totalForBar = $derived(actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0));
  let absentCount = $derived(selectedEtaData.absent_days_count || 0);
  let syncedPct = $derived(totalForBar > 0 ? (selectedCoverage.size / totalForBar) * 100 : 0);
  let completionStatusText = $derived(isComplete ? "Concluido" : "Em andamento");

  let hasFeaturedPub = $derived(hashState.seq != null);

  let iaYear = $derived(activeDate ? parseInt(activeDate.substring(0, 4)) : new Date().getFullYear());

  let qualityScore = $derived(qualityScores[selectedTribunal]);
  let qualityBadgeClass = $derived.by(() => {
    if (!qualityScore) return '';
    if (qualityScore.grade === 'A') return 'badge-success';
    if (qualityScore.grade === 'B') return 'badge-accent';
    if (qualityScore.grade === 'C') return 'badge-warning';
    return 'badge-error';
  });

  function exportCsv() {
    const rows = ["data,status"];
    snapshotDates.forEach(d => rows.push(`${d},coletado`));
    absentSet.forEach(d => rows.push(`${d},ausente`));
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cobertura-${selectedTribunal.toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function shareLink() {
    navigator.clipboard.writeText(window.location.href);
    alert("Link copiado para a area de transferencia.");
  }
</script>

<QueryProvider>
{#if !hashReady && typeof window !== 'undefined'}
  <div class="loading-container"><span class="spinner"></span></div>
{:else}
  <div>
    {#if hasFeaturedPub && activeDate}
      <DateDetail
        tribunalCode={tribunalCode}
        dateStr={activeDate}
        initialPage={hashState.page}
        initialSeq={hashState.seq}
      />
    {/if}

    <div class="toolbar">
      <div class="breadcrumbs">
        <ul>
          <li><a href={`${baseUrl}`}>CausaGanha</a></li>
          <li><a href={`${baseUrl}publicacoes`}>Publicacoes</a></li>
          <li>
            <select
              id="tribunal-select"
              value={selectedTribunal}
              onchange={handleTribunalChange}
              class="tribunal-select"
            >
              {#each TRIBUNAL_GROUPS as group}
                <optgroup label={group.name}>
                  {#each group.tribunals as t}
                    <option value={t}>{t}</option>
                  {/each}
                </optgroup>
              {/each}
            </select>
          </li>
        </ul>
      </div>
      <div class="toolbar-actions">
        <button
          class="btn btn-sm btn-ghost"
          onclick={exportCsv}
          title="Exportar CSV de Cobertura"
          aria-label="Exportar CSV"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
          Exportar CSV
        </button>
        <button
          class="btn btn-sm btn-ghost"
          onclick={shareLink}
          title="Copiar Link"
          aria-label="Compartilhar Link"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
          Compartilhar Link
        </button>
      </div>
    </div>

    <div class="title-section">
      <div>
        <h1 class="tribunal-title">{selectedTribunal}</h1>
        {#if qualityScore}
          <span
            class={`badge quality-badge ${qualityBadgeClass}`}
            title={`Completude: ${qualityScore.completeness}%\nRecencia: ${qualityScore.recency}%\nConsistencia: ${qualityScore.consistency}%`}
          >
            Qualidade: {qualityScore.grade}
          </span>
        {/if}
      </div>
    </div>

    <div class="stats">
      <div class="stat">
        <div class="stat-title">Progresso da Coleta</div>
        <div class="stat-value value-primary">{completionPct}%</div>
        <div class="stat-desc">
          <progress class="progress-bar progress-primary" value={Math.round(syncedPct)} max="100"></progress>
          <div class="progress-legend">
            <span>{selectedCoverage.size} itens sincronizados</span>
            <span>{absentCount} dias ausentes</span>
          </div>
        </div>
      </div>

      <div class="stat">
        <div class="stat-title">Status</div>
        <div class={`stat-value ${statusColor}`}>{completionStatusText}</div>
        <div class="stat-desc">{etaText}</div>
      </div>

      <div class="stat">
        <div class="stat-title">Dias Faltantes</div>
        <div class="stat-value">{actualMissingDays}</div>
        <div class="stat-desc">A partir de {genesisDate || "Desconhecida"}</div>
      </div>
    </div>

    <div class="tabs" role="tablist">
      <input type="radio" name="tribunal_tabs" role="tab" class="tab-input" aria-label="Calendario" id="tab-calendario" checked />
      <label for="tab-calendario" class="tab-label">Calendario</label>
      <div role="tabpanel" class="tab-content">
        <Heatmap
          globalStartDateStr={targetRange.start}
          globalEndDateStr={targetRange.end}
          tribunalStartDateStr={tribunalStartDate}
          coverageSet={selectedCoverage}
          tribunalName={selectedTribunal}
          baseUrl={baseUrl}
          velocityMetrics={{
            ...velocityMetrics,
            absentSet: absentSet
          }}
        />
      </div>

      <input type="radio" name="tribunal_tabs" role="tab" class="tab-input" aria-label="Estatisticas & Arquivo" id="tab-stats" />
      <label for="tab-stats" class="tab-label">Estatisticas & Arquivo</label>
      <div role="tabpanel" class="tab-content">
        <div class="two-col-grid">
          <div>
            <h3 class="subsection-title">Informacoes do Pipeline</h3>
            <div class="info-stack">
              <div>
                <small class="field-label">Data inicial do tribunal</small>
                <strong class="field-value">{genesisDate || "Desconhecida"}</strong>
              </div>

              {#if cursorDate && !isStopped}
                <div>
                  <small class="field-label">Cursor de varredura atual</small>
                  <strong class="field-value value-primary">{cursorDate}</strong>
                </div>
              {/if}

              {#if isStopped}
                <div class="alert alert-error">
                  <span>Pipeline interrompido (60 dias sem publicacoes identificadas).</span>
                </div>
              {/if}
            </div>
          </div>

          <div>
            <h3 class="subsection-title">Internet Archive</h3>
            <div class="ia-stack">
              <a
                href={`https://archive.org/details/djen-${selectedTribunal.toLowerCase()}-${iaYear}`}
                target="_blank"
                rel="noopener noreferrer"
                class="btn btn-outline btn-sm"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 1.25rem; height: 1.25rem;">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Ver colecao de {iaYear} no IA
              </a>
              <div class="data-access-wrapper">
                <DataAccessPanel
                  tribunalCode={selectedTribunal}
                  year={iaYear}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    {#if activeDate && !hasFeaturedPub}
      <DateDetail
        tribunalCode={tribunalCode}
        dateStr={activeDate}
        initialPage={hashState.page}
      />
    {/if}
  </div>
{/if}
</QueryProvider>

<style>
  /* Loading */
  .loading-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .spinner {
    display: inline-block;
    width: 2rem;
    height: 2rem;
    border: 2px solid var(--color-base-300);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Toolbar */
  .toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .toolbar-actions {
    display: flex;
    gap: 0.5rem;
  }

  /* Breadcrumbs */
  .breadcrumbs {
    margin-bottom: 0;
  }

  .breadcrumbs ul {
    display: flex;
    align-items: center;
    list-style: none;
    padding: 0;
    margin: 0;
    gap: 0.25rem;
    font-size: var(--font-size-sm);
  }

  .breadcrumbs li {
    display: flex;
    align-items: center;
  }

  .breadcrumbs li + li::before {
    content: '/';
    margin: 0 0.5rem;
    opacity: 0.4;
  }

  .breadcrumbs a {
    color: var(--color-primary);
    text-decoration: none;
  }

  .breadcrumbs a:hover {
    text-decoration: underline;
  }

  /* Tribunal select */
  .tribunal-select {
    border: none;
    background: transparent;
    padding: 0.25rem 0.5rem;
    font-size: var(--font-size-sm);
    cursor: pointer;
    font-weight: 600;
  }

  /* Buttons */

  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: var(--font-size-xs);
  }

  .btn-ghost {
    background: transparent;
    border-color: transparent;
    color: inherit;
  }

  .btn-ghost:hover {
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
  }

  /* Title section */
  .title-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 1.5rem;
  }

  .tribunal-title {
    font-size: var(--font-size-3xl, 1.875rem);
    font-weight: 700;
  }

  /* Badges */

  .quality-badge {
    margin-top: 0.5rem;
  }

  .badge-accent {
    background: var(--color-accent);
    color: var(--color-accent-content, #fff);
  }

  /* Stats */
  .stats {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    width: 100%;
    margin-bottom: 2rem;
  }

  @media (min-width: 768px) {
    .stats {
      flex-direction: row;
    }
  }

  .stat {
    padding: 1rem 1.5rem;
    flex: 1;
  }

  .stat-title {
    opacity: 0.6;
    font-size: var(--font-size-sm);
  }

  .stat-value {
    font-size: var(--font-size-2xl, 1.5rem);
    font-weight: 700;
  }

  .stat-desc {
    margin-top: 0.25rem;
    font-size: var(--font-size-sm);
    opacity: 0.7;
  }

  .value-primary {
    color: var(--color-primary);
  }

  .value-success {
    color: var(--color-success);
  }

  .value-warning {
    color: var(--color-warning);
  }

  /* Progress bars */
  .progress-bar {
    width: 100%;
    height: 0.5rem;
    appearance: none;
    border-radius: var(--radius-full);
  }

  .progress-bar::-webkit-progress-bar {
    background: var(--color-base-300);
    border-radius: var(--radius-full);
  }

  .progress-primary::-webkit-progress-value {
    background: var(--color-primary);
    border-radius: var(--radius-full);
  }

  .progress-legend {
    display: flex;
    justify-content: space-between;
    margin-top: 0.25rem;
    font-size: var(--font-size-xs);
    opacity: 0.6;
  }

  /* Tabs */
  .tabs {
    margin-bottom: 2rem;
  }

  .tab-input {
    display: none;
  }

  .tab-label {
    display: inline-block;
    padding: 0.75rem 1.25rem;
    font-weight: 600;
    font-size: var(--font-size-sm);
    cursor: pointer;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: var(--radius-box) var(--radius-box) 0 0;
    margin-right: 0.25rem;
    position: relative;
    top: 1px;
    background: transparent;
    opacity: 0.6;
  }

  .tab-input:checked + .tab-label {
    background: var(--color-base-100);
    border-color: var(--color-base-300);
    opacity: 1;
  }

  .tab-content {
    display: none;
    background: var(--color-base-100);
    border: 1px solid var(--color-base-300);
    border-radius: 0 var(--radius-box) var(--radius-box) var(--radius-box);
    padding: 1rem;
    box-shadow: var(--shadow-sm);
  }

  @media (min-width: 768px) {
    .tab-content {
      padding: 1.5rem;
    }
  }

  .tab-input:checked + .tab-label + .tab-content {
    display: block;
  }

  /* Two column grid */
  .two-col-grid {
    display: grid;
    gap: 2rem;
  }

  @media (min-width: 768px) {
    .two-col-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  /* Subsections */
  .subsection-title {
    font-size: var(--font-size-xl, 1.25rem);
    margin-bottom: 1rem;
  }

  .info-stack {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .ia-stack {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .field-label {
    opacity: 0.5;
    display: block;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-size: var(--font-size-xs);
  }

  .field-value {
    font-size: var(--font-size-sm);
  }

  /* Data access wrapper */
  .data-access-wrapper {
    background: var(--color-base-200);
    padding: 1rem;
    border-radius: var(--radius-box);
  }

  /* Alert */
  .alert {
    padding: 1rem;
    border-radius: var(--radius-box);
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .alert-error {
    background: var(--color-error);
    color: var(--color-error-content, #fff);
  }

  @media (min-width: 640px) {
  }
</style>
