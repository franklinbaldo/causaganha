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

      <div className="flex justify-between items-center mb-4">
        <div className="breadcrumbs mb-0">
          <ul>
            <li><a href={`${baseUrl}`}>CausaGanha</a></li>
            <li><a href={`${baseUrl}publicacoes`}>Publicações</a></li>
            <li>
              <select
                id="tribunal-select" value={selectedTribunal}
                onChange={handleTribunalChange}
                className="select select-ghost select-sm">
                {TRIBUNAL_GROUPS.map(group => (
                  <optgroup key={group.name} label={group.name}>
                    {group.tribunals.map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </li>
          </ul>
        </div>
        <div className="flex gap-2">
          <button
            className="btn btn-sm btn-ghost"
            onClick={() => {
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
            }}
            title="Exportar CSV de Cobertura"
            aria-label="Exportar CSV"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            Exportar CSV
          </button>
          <button
            className="btn btn-sm btn-ghost"
            onClick={() => {
              navigator.clipboard.writeText(window.location.href);
              alert("Link copiado para a área de transferência.");
            }}
            title="Copiar Link"
            aria-label="Compartilhar Link"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
            Compartilhar Link
          </button>
        </div>
      </div>

      <div className="flex justify-between items-end mb-6">
        <div>
          <h1 className="text-3xl font-bold">{selectedTribunal}</h1>
          {qualityScores[selectedTribunal] && (
            <span
              className={`badge mt-2 ${qualityScores[selectedTribunal].grade === 'A' ? "badge-success" : qualityScores[selectedTribunal].grade === 'B' ? "badge-accent" : qualityScores[selectedTribunal].grade === 'C' ? "badge-warning" : "badge-error"}`}
              title={`Completude: ${qualityScores[selectedTribunal].completeness}%\nRecência: ${qualityScores[selectedTribunal].recency}%\nConsistência: ${qualityScores[selectedTribunal].consistency}%`}>
              Qualidade: {qualityScores[selectedTribunal].grade}
            </span>
          )}
        </div>
      </div>

      <div className="stats stats-vertical md:stats-horizontal shadow-sm border border-base-300 w-full mb-8">
        <div className="stat">
          <div className="stat-title">Progresso da Coleta</div>
          <div className="stat-value text-primary">{completionPct}%</div>
          <div className="stat-desc mt-1">
            <progress className="progress progress-primary w-full" value={Math.round(syncedPct)} max="100"></progress>
            <div className="flex justify-between mt-1">
              <span>{selectedCoverage.size} itens sincronizados</span>
              <span>{absentCount} dias ausentes</span>
            </div>
          </div>
        </div>

        <div className="stat">
          <div className="stat-title">Status</div>
          <div className={`stat-value ${statusColor}`}>{completionStatusText}</div>
          <div className="stat-desc">{etaText}</div>
        </div>

        <div className="stat">
          <div className="stat-title">Dias Faltantes</div>
          <div className="stat-value">{actualMissingDays}</div>
          <div className="stat-desc">A partir de {genesisDate || "Desconhecida"}</div>
        </div>
      </div>

      <div role="tablist" className="tabs tabs-lifted mb-8">
        <input type="radio" name="tribunal_tabs" role="tab" className="tab font-semibold" aria-label="Calendário" defaultChecked />
        <div role="tabpanel" className="tab-content bg-base-100 border-base-300 rounded-box p-4 md:p-6 shadow-sm">
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
        </div>

        <input type="radio" name="tribunal_tabs" role="tab" className="tab font-semibold" aria-label="Estatísticas & Arquivo" />
        <div role="tabpanel" className="tab-content bg-base-100 border-base-300 rounded-box p-4 md:p-6 shadow-sm">
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h3 className="text-xl mb-4">Informações do Pipeline</h3>
              <div className="space-y-4">
                <div>
                  <small className="opacity-50 block uppercase tracking-widest text-xs">Data inicial do tribunal</small>
                  <strong className="text-sm">{genesisDate || "Desconhecida"}</strong>
                </div>

                {cursorDate && !isStopped && (
                  <div>
                    <small className="opacity-50 block uppercase tracking-widest text-xs">Cursor de varredura atual</small>
                    <strong className="text-primary text-sm">{cursorDate}</strong>
                  </div>
                )}

                {isStopped && (
                  <div className="alert alert-error">
                    <span>Pipeline interrompido (60 dias sem publicações identificadas).</span>
                  </div>
                )}
              </div>
            </div>

            <div>
              <h3 className="text-xl mb-4">Internet Archive</h3>
              {(() => {
                const iaYear = activeDate ? parseInt(activeDate.substring(0, 4)) : new Date().getFullYear();
                return (
                  <div className="space-y-6">
                    <a
                      href={`https://archive.org/details/djen-${selectedTribunal.toLowerCase()}-${iaYear}`} target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-outline btn-sm w-full sm:w-auto">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '1.25rem', height: '1.25rem' }}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                      Ver coleção de {iaYear} no IA
                    </a>
                    <div className="bg-base-200 p-4 rounded-lg">
                      <DataAccessPanel
                        tribunalCode={selectedTribunal} year={iaYear}
                      />
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
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
