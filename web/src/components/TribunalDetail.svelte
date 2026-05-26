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
  import TribunalStatsBar from './TribunalStatsBar.svelte';

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
    if (actualMissingDays === 0 && expectedDays > 0) return "Concluído";
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
  let completionStatusText = $derived(isComplete ? "Concluído" : "Em andamento");

  let hasFeaturedPub = $derived(hashState.seq != null);

  let iaYear = $derived(activeDate ? parseInt(activeDate.substring(0, 4)) : new Date().getFullYear());

  let qualityScore = $derived(qualityScores[selectedTribunal]);
  let qualityTone = $derived.by(() => {
    if (!qualityScore) return '';
    if (qualityScore.grade === 'A') return 'success';
    if (qualityScore.grade === 'B') return 'info';
    if (qualityScore.grade === 'C') return 'warning';
    return 'error';
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

  let shareLinkCopied = $state(false);
  let shareTimeoutId: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    return () => {
      if (shareTimeoutId) clearTimeout(shareTimeoutId);
    };
  });

  function shareLink() {
    navigator.clipboard.writeText(window.location.href);
    if (shareTimeoutId) clearTimeout(shareTimeoutId);
    shareLinkCopied = true;
    shareTimeoutId = setTimeout(() => {
      shareLinkCopied = false;
      shareTimeoutId = null;
    }, 2000);
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
          <li><a href={`${baseUrl}publicacoes`}>Publicações</a></li>
          <li>{selectedTribunal}</li>
        </ul>
      </div>
    </div>

    <div class="title-section">
      <div class="title-main">
        <h1 class="tribunal-title">{selectedTribunal}</h1>
        {#if qualityScore}
          <mark
            data-tone={qualityTone}
            class="quality-badge"
            title={`Completude: ${qualityScore.completeness}%\nRecência: ${qualityScore.recency}%\nConsistência: ${qualityScore.consistency}%`}
          >
            Qualidade: {qualityScore.grade}
          </mark>
        {/if}
      </div>
      <div class="title-actions">
        <div class="tribunal-switcher">
          <label for="tribunal-select" class="switcher-label">Trocar tribunal</label>
          <select
            id="tribunal-select"
            value={selectedTribunal}
            onchange={handleTribunalChange}
            class="tribunal-select-title"
          >
            {#each TRIBUNAL_GROUPS as group}
              <optgroup label={group.name}>
                {#each group.tribunals as t}
                  <option value={t}>{t}</option>
                {/each}
              </optgroup>
            {/each}
          </select>
        </div>
        <div class="toolbar-actions">
          <button
            class="outline secondary action-btn"
            onclick={exportCsv}
            title="Exportar CSV de Cobertura"
            aria-label="Exportar CSV"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Exportar CSV
          </button>
          <button
            class="outline secondary action-btn"
            onclick={shareLink}
            title="Copiar Link"
            aria-label="Compartilhar Link"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
            {shareLinkCopied ? 'Copiado!' : 'Compartilhar Link'}
          </button>
        </div>
      </div>
    </div>

    <TribunalStatsBar
      {completionPct}
      {syncedPct}
      coverageSize={selectedCoverage.size}
      {absentCount}
      {statusColor}
      {completionStatusText}
      {etaText}
      {actualMissingDays}
      {genesisDate}
    />

    <div class="tabs" role="tablist">
      <input type="radio" name="tribunal_tabs" role="tab" class="tab-input" aria-label="Calendário" id="tab-calendario" checked />
      <label for="tab-calendario" class="tab-label">Calendário</label>
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

      <input type="radio" name="tribunal_tabs" role="tab" class="tab-input" aria-label="Estatísticas & Arquivo" id="tab-stats" />
      <label for="tab-stats" class="tab-label">Estatísticas & Arquivo</label>
      <div role="tabpanel" class="tab-content">
        <div class="two-col-grid">
          <div>
            <h3 class="subsection-title">Informações do Pipeline</h3>
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
                <p><mark data-tone="error">Pipeline interrompido (60 dias sem publicações identificadas).</mark></p>
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
                role="button"
                class="outline secondary action-btn"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="icon-sm">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Ver coleção de {iaYear} no IA
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
