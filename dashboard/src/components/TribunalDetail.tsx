import { useState, useEffect } from 'preact/compat';
import { useDataRefresh } from '../lib/useDataRefresh';
import { TRIBUNAIS, TRIBUNAL_GROUPS } from '../lib/tribunais';
import { toDateString } from '../lib/dateUtils';
import { Heatmap, VelocityTimeline } from './Heatmap';
import { calculateVelocityAndRegression } from '../lib/velocityCalc';
import { DateDetail } from './DateDetail';
import { DataAccessPanel } from './DataAccessPanel';

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

export function TribunalDetail({ tribunalCode, initialCoverage, initialEtas, initialTargetRange, initialStartDates, initialQualityScores }: TribunalDetailProps) {
  const { data: allData } = useDataRefresh(null, null);
  const [selectedTribunal, setSelectedTribunal] = useState<string>(tribunalCode.toUpperCase());
  const [hashState, setHashState] = useState<HashState>({ date: null, page: null, seq: null });
  const [hashReady, setHashReady] = useState<boolean>(false);

  // Read hash on mount + listen for changes
  useEffect(() => {
    setHashState(parseHash());
    setHashReady(true);
    const onHashChange = () => setHashState(parseHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  // Don't render content until hash is read (prevents flash of wrong date)
  // Disable hash loading barrier when running under test/ssg, otherwise the page will be completely blank
  if (!hashReady && typeof window !== 'undefined') {
    return <div className="flex justify-center p-8"><span className="loading loading-spinner loading-lg"></span></div>;
  }

  const coverage = allData?.tribunalCoverage ?? initialCoverage ?? {};
  const absentCoverage = allData?.tribunalAbsentCoverage ?? {};
  const etas = allData?.tribunalEtas ?? initialEtas ?? {};
  const startDates = allData?.tribunalStartDates ?? initialStartDates ?? {};
  const qualityScores = allData?.tribunalQualityScores ?? initialQualityScores ?? {};
  const iaSnapshot = allData?.iaSnapshot;

  // Date from hash, or most recent from snapshot
  let activeDate = hashState.date;
  if (!activeDate && iaSnapshot?.items) {
    for (const item of Object.values(iaSnapshot.items)) {
      if (item.tribunal === selectedTribunal) {
        if (!activeDate || item.latest_date> activeDate) {
          activeDate = item.latest_date;
        }
      }
    }
  }

  // Derive targetRange dynamically — no hardcoded dates
  const backfillTargetRange = allData?.targetRange ?? initialTargetRange;
  const today = toDateString(new Date());
  const targetRange = {
    start: backfillTargetRange?.start || "2024-01-01",
    end: backfillTargetRange?.end || today,
  };

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  const handleTribunalChange = (e: Event) => {
    const newTribunal = (e.target as HTMLSelectElement).value;
    if (!TRIBUNAIS.includes(newTribunal)) return;
    setSelectedTribunal(newTribunal);
    window.location.href = `${baseUrl}publicacoes/${encodeURIComponent(newTribunal.toLowerCase())}`;
  };

  // Build coverage from IA snapshot (real ZIPs on IA) — prefer over backfill data
  const snapshotDates = new Set();
  if (iaSnapshot?.items) {
    for (const item of Object.values(iaSnapshot.items)) {
      if (item.tribunal === selectedTribunal) {
        item.dates.forEach(d => snapshotDates.add(d));
      }
    }
  }
  const selectedCoverage = snapshotDates.size> 0 ? snapshotDates : new Set(coverage[selectedTribunal] || []);
  const selectedEtaData = etas[selectedTribunal] || { missing_days: null, velocity_14d: 0, eta_days: null };
  const tribunalStartDate = startDates[selectedTribunal] || selectedEtaData.genesis_date;

  // Calculate expected days from tribunal start to target end
  let expectedDays = 0;
  if (tribunalStartDate) {
    const start = new Date(tribunalStartDate + "T00:00:00Z");
    const end = new Date(targetRange.end + "T00:00:00Z");
    if (start <= end) {
      expectedDays = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
    }
  }

  const actualMissingDays = selectedEtaData.missing_days !== null
    ? selectedEtaData.missing_days
    : Math.max(0, expectedDays - selectedCoverage.size);

  const isStopped = selectedEtaData.stopped || false;
  const cursorDate = selectedEtaData.cursor_date;
  const completionPct = selectedEtaData.completion_pct || 0;
  const genesisDate = selectedEtaData.genesis_date || tribunalStartDate;

  const velocityMetrics = calculateVelocityAndRegression(selectedCoverage, targetRange.end, tribunalStartDate);

  let dynamicEtaDays = selectedEtaData.eta_days;
  if (velocityMetrics && velocityMetrics.currentVelocity> 0 && actualMissingDays> 0) {
    dynamicEtaDays = Math.ceil(actualMissingDays / (velocityMetrics.currentVelocity / 7));
  }

  let etaText = "Pendente";
  if (actualMissingDays === 0 && expectedDays> 0) {
    etaText = "Concluído";
  } else if (dynamicEtaDays) {
    if (dynamicEtaDays < 30) {
      etaText = `~${dynamicEtaDays} dias`;
    } else {
      const months = Math.round(dynamicEtaDays / 30);
      etaText = `~${months} ${months> 1 ? 'meses' : 'mes'}`;
    }
  }

  const isComplete = actualMissingDays === 0 && expectedDays> 0;
  const statusColor = isComplete ? "text-success" : "text-warning";

  const absentList = absentCoverage[selectedTribunal] || [];
  const absentSet = new Set(absentList);

  const totalForBar = actualMissingDays + selectedCoverage.size + (selectedEtaData.absent_days_count || 0);
  const absentCount = selectedEtaData.absent_days_count || 0;
  const syncedPct = totalForBar> 0 ? (selectedCoverage.size / totalForBar) * 100 : 0;
  const completionStatusText = isComplete ? "Concluído" : "Em andamento";

  const hasFeaturedPub = hashState.seq != null;

  return (
    <div>
      {/* Featured publication at the very top when deep-linked */}
      {hasFeaturedPub && activeDate && (
        <DateDetail
          tribunalCode={tribunalCode} dateStr={activeDate}
          initialPage={hashState.page}
          initialSeq={hashState.seq}
        />
      )}

      <div className="breadcrumbs">
        <ul>
          <li><a href={`${baseUrl}`}>CausaGanha</a></li>
          <li><a href={`${baseUrl}publicacoes`}>Publicações</a></li>
          <li>{selectedTribunal}</li>
        </ul>
      </div>

      <div className="grid">
        {/* Sidebar */}
        <aside>
          <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
            <label htmlFor="tribunal-select">
              Tribunal
            </label>
            <select
              id="tribunal-select" value={selectedTribunal}
              onChange={handleTribunalChange}
              className="select select-bordered">
              {TRIBUNAL_GROUPS.map(group => (
                <optgroup key={group.name} label={group.name}>
                  {group.tribunals.map(t => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </optgroup>
              ))}
            </select>

            <div className="mb-6">
              <div className="flex justify-between items-baseline items-center mb-2">
                <h3 className="m-0 text-2xl">{selectedTribunal}</h3>
                {qualityScores[selectedTribunal] && (
                  <span
                    className={
                      qualityScores[selectedTribunal].grade === 'A' ? "badge badge-success" :
                      qualityScores[selectedTribunal].grade === 'B' ? "badge badge-accent" :
                      qualityScores[selectedTribunal].grade === 'C' ? "badge badge-warning" :
                      qualityScores[selectedTribunal].grade === 'D' ? "badge badge-error" :
                      "badge"
                    }
                    title={`Completude: ${qualityScores[selectedTribunal].completeness}%\nRecência: ${qualityScores[selectedTribunal].recency}%\nConsistência: ${qualityScores[selectedTribunal].consistency}%`}>
                    Nota {qualityScores[selectedTribunal].grade}
                  </span>
                )}
              </div>
            </div>

            <div className="mb-4">
              <small className="opacity-50 block uppercase tracking-widest text-xs">Data inicial</small>
              <strong className="text-sm">{genesisDate || "Desconhecida"}</strong>
            </div>

            <div className="mb-4">
              <div className="flex justify-between items-baseline mb-2">
                <small className="opacity-50 uppercase tracking-widest text-xs">Progresso</small>
                <strong className="text-primary text-sm">{completionPct}%</strong>
              </div>
              <progress
                value={Math.round(syncedPct)}
                max="100"
                title={`Sincronizados: ${selectedCoverage.size} ZIPs`}
                className="progress progress-primary mb-2">
              </progress>
              <div className="opacity-50 text-xs flex justify-between items-baseline">
                <span>{selectedCoverage.size} sincronizados</span>
                <span>{absentCount} ausentes</span>
              </div>
            </div>

            <div className="mb-4">
              <small className="opacity-50 block uppercase tracking-widest text-xs">Status</small>
              <strong className={`text-sm ${statusColor}`}>{completionStatusText}: {etaText}</strong>
            </div>

            <div className="mb-4">
              <small className="opacity-50 block uppercase tracking-widest text-xs">Dias faltantes</small>
              <strong className="text-sm">{actualMissingDays} dias</strong>
            </div>

            {cursorDate && !isStopped && (
              <div className="mb-4">
                <small className="opacity-50 block uppercase tracking-widest text-xs">Cursor de varredura</small>
                <strong className="text-primary text-sm">{cursorDate}</strong>
              </div>
            )}

            {isStopped && (
              <div className="mb-4">
                <span className="badge badge-error block text-center p-2">
                  Pipeline interrompido (60 dias sem publicações)
                </span>
              </div>
            )}

            {/* IA item link */}
            {(() => {
              // Derive year from active date or fall back to current year
              const iaYear = activeDate ? parseInt(activeDate.substring(0, 4)) : new Date().getFullYear();
              return (
                <div className="mt-6 pt-6 border-t border-base-300">
                  <a
                    href={`https://archive.org/details/djen-${selectedTribunal.toLowerCase()}-${iaYear}`} target="_blank"
                    rel="noopener noreferrer"
                    className="secondary flex items-center gap-2 mb-4">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '1.25rem', height: '1.25rem' }}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Ver no Internet Archive
                  </a>
                  <DataAccessPanel
                    tribunalCode={selectedTribunal} year={iaYear}
                  />
                </div>
              );
            })()}
          </div></div>
        </aside>

        {/* Main: Heatmap area */}
        <main>
          <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
            <Heatmap
              globalStartDateStr={targetRange.start} globalEndDateStr={targetRange.end}
              tribunalStartDateStr={tribunalStartDate}
              coverageSet={selectedCoverage}
              tribunalName={selectedTribunal}
              baseUrl={baseUrl}
              velocityMetrics={{
                ...velocityMetrics,
                absentSet: absentSet
              }}
            />
          </div></div>
        </main>
      </div>

      {/* Publications for active date (only when not showing featured pub above) */}
      {activeDate && !hasFeaturedPub && (
        <DateDetail
          tribunalCode={tribunalCode} dateStr={activeDate}
          initialPage={hashState.page}
        />
      )}
    </div>
  );
}
