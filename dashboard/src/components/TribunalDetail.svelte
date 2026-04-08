<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createDataRefresh } from '../lib/dataRefreshStore';
  import { TRIBUNAIS, TRIBUNAL_GROUPS } from '../lib/tribunais';
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
    return {
      date: parts[0] || null,
      page: parts[1] ? parseInt(parts[1]) : null,
      seq: parts[2] ? parseInt(parts[2]) : null,
    };
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

  const store = createDataRefresh(null, null);
  onMount(() => store.start());
  onDestroy(() => store.stop());

  let selectedTribunal = $state(tribunalCode.toUpperCase());
  let hashState = $state<HashState>({ date: null, page: null, seq: null });
  let hashReady = $state(false);

  onMount(() => {
    hashState = parseHash();
    hashReady = true;
    const onHashChange = () => { hashState = parseHash(); };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  });

  let allData = $derived($store.data);

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

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
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
  let statusColor = $derived(isComplete ? "text-success" : "text-warning");

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

{#if !hashReady && typeof window !== 'undefined'}
  <div class="flex justify-center p-8"><span class="loading loading-spinner loading-lg"></span></div>
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

    <div class="flex justify-between items-center mb-4">
      <div class="breadcrumbs mb-0">
        <ul>
          <li><a href={`${baseUrl}`}>CausaGanha</a></li>
          <li><a href={`${baseUrl}publicacoes`}>Publicacoes</a></li>
          <li>
            <select
              id="tribunal-select"
              value={selectedTribunal}
              onchange={handleTribunalChange}
              class="select select-ghost select-sm"
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
      <div class="flex gap-2">
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

    <div class="flex justify-between items-end mb-6">
      <div>
        <h1 class="text-3xl font-bold">{selectedTribunal}</h1>
        {#if qualityScore}
          <span
            class={`badge mt-2 ${qualityBadgeClass}`}
            title={`Completude: ${qualityScore.completeness}%\nRecencia: ${qualityScore.recency}%\nConsistencia: ${qualityScore.consistency}%`}
          >
            Qualidade: {qualityScore.grade}
          </span>
        {/if}
      </div>
    </div>

    <div class="stats stats-vertical md:stats-horizontal shadow-sm border border-base-300 w-full mb-8">
      <div class="stat">
        <div class="stat-title">Progresso da Coleta</div>
        <div class="stat-value text-primary">{completionPct}%</div>
        <div class="stat-desc mt-1">
          <progress class="progress progress-primary w-full" value={Math.round(syncedPct)} max="100"></progress>
          <div class="flex justify-between mt-1">
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

    <div role="tablist" class="tabs tabs-lifted mb-8">
      <input type="radio" name="tribunal_tabs" role="tab" class="tab font-semibold" aria-label="Calendario" checked />
      <div role="tabpanel" class="tab-content bg-base-100 border-base-300 rounded-box p-4 md:p-6 shadow-sm">
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

      <input type="radio" name="tribunal_tabs" role="tab" class="tab font-semibold" aria-label="Estatisticas & Arquivo" />
      <div role="tabpanel" class="tab-content bg-base-100 border-base-300 rounded-box p-4 md:p-6 shadow-sm">
        <div class="grid md:grid-cols-2 gap-8">
          <div>
            <h3 class="text-xl mb-4">Informacoes do Pipeline</h3>
            <div class="space-y-4">
              <div>
                <small class="opacity-50 block uppercase tracking-widest text-xs">Data inicial do tribunal</small>
                <strong class="text-sm">{genesisDate || "Desconhecida"}</strong>
              </div>

              {#if cursorDate && !isStopped}
                <div>
                  <small class="opacity-50 block uppercase tracking-widest text-xs">Cursor de varredura atual</small>
                  <strong class="text-primary text-sm">{cursorDate}</strong>
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
            <h3 class="text-xl mb-4">Internet Archive</h3>
            <div class="space-y-6">
              <a
                href={`https://archive.org/details/djen-${selectedTribunal.toLowerCase()}-${iaYear}`}
                target="_blank"
                rel="noopener noreferrer"
                class="btn btn-outline btn-sm w-full sm:w-auto"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 1.25rem; height: 1.25rem;">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                Ver colecao de {iaYear} no IA
              </a>
              <div class="bg-base-200 p-4 rounded-lg">
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
