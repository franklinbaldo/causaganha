<script lang="ts">
  import { onMount } from 'svelte';
  import { TRIBUNAIS, TRIBUNAL_GROUPS } from '../lib/tribunais';
  import { toDateString, daysBetweenIso, latestIsoDate } from '../lib/dateUtils';
  import Heatmap from './Heatmap.svelte';
  import { calculateVelocityAndRegression } from '../lib/velocityCalc';
  import DateDetail from './DateDetail.svelte';
  import DataAccessPanel from './DataAccessPanel.svelte';
  import TribunalStatsBar from './TribunalStatsBar.svelte';
  import { buildTribunalAttentionCards } from '../lib/coverageInsights';

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
    initialUploadedDates: string[];
    initialAbsentDates: string[];
    initialStartDate: string | null;
  }

  let {
    tribunalCode,
    initialUploadedDates,
    initialAbsentDates,
    initialStartDate,
  }: TribunalDetailProps = $props();

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

  // Fonte única: contrato canônico tribunal_calendar (sync-manifest.parquet),
  // já filtrado por tribunal em build-time por [tribunal].astro. Sem polling
  // ao vivo do IA — mesmo padrão estático de /stats e /advogados (issue #809).
  let coverageSet = $derived(new Set(initialUploadedDates));
  let absentSet = $derived(new Set(initialAbsentDates));
  let tribunalStartDate = $derived(initialStartDate);

  let activeDate = $derived(hashState.date || latestIsoDate(initialUploadedDates));

  let today = $derived(toDateString(new Date()));
  let targetRange = $derived({ start: "2024-01-01", end: today });

  const BASE = import.meta.env.BASE_URL;
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  function handleTribunalChange(e: Event) {
    const newTribunal = (e.target as HTMLSelectElement).value;
    if (!TRIBUNAIS.includes(newTribunal)) return;
    selectedTribunal = newTribunal;
    window.location.href = `${baseUrl}publicacoes/${encodeURIComponent(newTribunal.toLowerCase())}`;
  }

  let expectedDays = $derived(
    tribunalStartDate ? Math.max(0, daysBetweenIso(tribunalStartDate, targetRange.end) + 1) : 0
  );

  let absentCount = $derived(absentSet.size);
  let actualMissingDays = $derived(Math.max(0, expectedDays - coverageSet.size - absentCount));

  // "Pipeline parado" fica indisponível sem uma data de referência: nenhum
  // dia arquivado ou confirmado ausente nos últimos STOPPED_THRESHOLD_DAYS
  // dias do target range. Sem fonte canônica para o estado real do pipeline
  // (cursor de varredura) — isso é estado de execução do engine, não dado
  // arquivado, então não há contrato .qmd possível para ele; o bloco de
  // "cursor atual" foi removido (nunca teve dado real em produção, ver PR).
  const STOPPED_THRESHOLD_DAYS = 60;
  let isStopped = $derived.by(() => {
    const latest = latestIsoDate(initialUploadedDates, initialAbsentDates);
    if (!latest) return false;
    return daysBetweenIso(latest, targetRange.end) > STOPPED_THRESHOLD_DAYS;
  });

  // Clampado a [0, 100]: coverageSet/absentSet podem conter datas fora da
  // janela [tribunalStartDate, targetRange.end] (tribunal_start_dates.json é
  // um arquivo curado, pode não refletir o início real rastreado no
  // manifesto), o que sem o clamp renderiria porcentagens acima de 100%.
  let completionPct = $derived(
    expectedDays > 0
      ? Math.min(100, Math.round(((coverageSet.size + absentCount) / expectedDays) * 1000) / 10)
      : 0
  );

  let velocityMetrics = $derived(calculateVelocityAndRegression(coverageSet, targetRange.end, tribunalStartDate ?? undefined));

  let dynamicEtaDays = $derived.by(() => {
    let eta: number | null = null;
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

  let totalForBar = $derived(actualMissingDays + coverageSet.size + absentCount);
  let syncedPct = $derived(totalForBar > 0 ? (coverageSet.size / totalForBar) * 100 : 0);
  let completionStatusText = $derived(isComplete ? "Concluído" : "Em andamento");

  let tribunalAttentionCards = $derived(buildTribunalAttentionCards({
    tribunal: selectedTribunal,
    missingDays: actualMissingDays,
    absentCount,
    expectedDays,
    coverageSize: coverageSet.size,
    completionPct,
    velocityRegressionPct: velocityMetrics?.regressionDrop,
    isStopped,
  }));

  let hasFeaturedPub = $derived(hashState.seq != null);

  let iaYear = $derived(activeDate ? parseInt(activeDate.substring(0, 4)) : new Date().getFullYear());

  function exportCsv() {
    const rows = ["data,status"];
    initialUploadedDates.forEach(d => rows.push(`${d},coletado`));
    initialAbsentDates.forEach(d => rows.push(`${d},ausente`));
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

{#if !hashReady && typeof window !== 'undefined'}
  <p aria-busy="true">Carregando...</p>
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

    <hgroup>
      <h1>{selectedTribunal}</h1>
    </hgroup>
    <div>
      <div class="tribunal-switcher">
        <label for="tribunal-select">Trocar tribunal</label>
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
          class="outline secondary"
          onclick={exportCsv}
          title="Exportar CSV de Cobertura"
          aria-label="Exportar CSV"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
          Exportar CSV
        </button>
        <button
          class="outline secondary"
          onclick={shareLink}
          title="Copiar Link"
          aria-label="Compartilhar Link"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
          {shareLinkCopied ? 'Copiado!' : 'Compartilhar Link'}
        </button>
      </div>
    </div>

    <TribunalStatsBar
      {completionPct}
      {syncedPct}
      coverageSize={coverageSet.size}
      {absentCount}
      {statusColor}
      {completionStatusText}
      {etaText}
      {actualMissingDays}
      genesisDate={tribunalStartDate}
    />

    {#if tribunalAttentionCards.length > 0}
      <section class="auto-grid" aria-label="Atenção da cobertura do tribunal">
        {#each tribunalAttentionCards as card}
          <article class="attention-card" data-tone={card.tone}>
            <header>
              <strong><span aria-hidden="true">{card.icon}</span> {card.title}</strong>
              <span class="badge" data-tone={card.tone}>{card.summary}</span>
            </header>
            <p>{card.impact}</p>
            <p>{card.cause}</p>
            <p><strong>{card.action}</strong></p>
          </article>
        {/each}
      </section>
    {/if}

    <details open>
      <summary>Calendário</summary>
      <Heatmap
        globalStartDateStr={targetRange.start}
        globalEndDateStr={targetRange.end}
        tribunalStartDateStr={tribunalStartDate}
        {coverageSet}
        tribunalName={selectedTribunal}
        baseUrl={baseUrl}
        velocityMetrics={{
          ...velocityMetrics,
          absentSet: absentSet
        }}
      />
    </details>

    <details>
      <summary>Estatísticas &amp; Arquivo</summary>
      <div class="two-col-grid">
        <div>
          <h4>Informações do Pipeline</h4>
          <dl>
            <dt>Data inicial do tribunal</dt>
            <dd><strong>{tribunalStartDate || "Desconhecida"}</strong></dd>
          </dl>

          {#if isStopped}
            <p><mark data-tone="error">Pipeline interrompido (60 dias sem publicações identificadas).</mark></p>
          {/if}
        </div>

        <div>
          <h4>Internet Archive</h4>
          <a
            href={`https://archive.org/details/djen-${selectedTribunal.toLowerCase()}-${iaYear}`}
            target="_blank"
            rel="noopener noreferrer"
            role="button"
            class="outline secondary"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Ver coleção de {iaYear} no IA
          </a>
          <DataAccessPanel
            tribunalCode={selectedTribunal}
            year={iaYear}
          />
        </div>
      </div>
    </details>

    {#if activeDate && !hasFeaturedPub}
      <DateDetail
        tribunalCode={tribunalCode}
        dateStr={activeDate}
        initialPage={hashState.page}
      />
    {/if}
  </div>
{/if}
