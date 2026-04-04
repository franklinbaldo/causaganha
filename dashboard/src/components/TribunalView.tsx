import { useMemo, useState } from 'preact/hooks';
import { useDataRefresh } from '../lib/useDataRefresh';
import { TRIBUNAL_GROUPS } from '../lib/tribunais';

interface TribunalViewProps {
  initialPipeline: any;
  initialProgressByYear: Record<string, any> | null;
  initialVolume: any;
  initialIaSnapshot: any;
}

export function TribunalView({ initialPipeline, initialProgressByYear, initialVolume, initialIaSnapshot }: TribunalViewProps) {
  const { data: allData } = useDataRefresh(null, null);

  const pipeline = allData?.cacheData?.today?.pipeline ?? initialPipeline;
  const progressByYear = allData?.progressByYear ?? initialProgressByYear;
  const volume = allData?.volume ?? initialVolume;
  const iaSnapshot = allData?.iaSnapshot ?? initialIaSnapshot;

  return (
    <OverviewGrid
      pipeline={pipeline} progressByYear={progressByYear}
      volume={volume}
      iaSnapshot={iaSnapshot}
    />
  );
}

interface OverviewGridProps {
  pipeline: any;
  progressByYear: Record<string, any> | null;
  volume: any;
  iaSnapshot: any;
}

function OverviewGrid({ pipeline, progressByYear, volume, iaSnapshot }: OverviewGridProps) {
  const [query, setQuery] = useState('');

  // Prefer IA snapshot data (fresh, direct from IA) over pipeline/backfill data
  const snap = iaSnapshot?.summary;
  const totalZips = snap?.total_zips || pipeline?.total_zips || 0;
  const totalGB = snap?.total_size_gb || volume?.total_gb || 0;
  const tribunalsWithData = snap?.tribunals_with_data || 0;
  const latestDate = snap?.latest_collection_date;
  const snapshotAge = iaSnapshot?.generated_at;

  // Per-tribunal zip counts from snapshot
  const snapshotItems = iaSnapshot?.items || {};
  const snapshotByYear = iaSnapshot?.by_year || {};

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';
  const normalizedQuery = query.trim().toLowerCase();
  const filteredGroups = useMemo(() => {
    return TRIBUNAL_GROUPS
      .map(group => ({
        ...group,
        tribunals: group.tribunals.filter(tribunal => {
          if (!normalizedQuery) return true;
          return tribunal.toLowerCase().includes(normalizedQuery);
        }),
      }))
      .filter(group => group.tribunals.length> 0);
  }, [normalizedQuery]);

  return (
    <div>
      {/* Global Progress Banner */}
      <article>
        <header>
          <hgroup>
            <h2>Progresso do Arquivo</h2>
            <p>
              {totalZips.toLocaleString()} ZIPs no Internet Archive
            </p>
          </hgroup>
          {latestDate && (
            <p className="text-muted" style={{ fontSize: '0.875rem' }}>
              Última coleta: {latestDate}
              {snapshotAge && <span> | Instantâneo: {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>}
            </p>
          )}
        </header>

        {/* Quick Stats Grid */}
        <div className="grid">
           <article style={{ margin: 0 }}>
              <div className="stat-value text-primary">{totalZips.toLocaleString()}</div>
              <p className="stat-label">ZIPs no IA</p>
           </article>
           <article style={{ margin: 0 }}>
              <div className="stat-value">{totalGB.toFixed(1)} GB</div>
              <p className="stat-label">Volume</p>
           </article>
           <article style={{ margin: 0 }}>
              <div className="stat-value text-success">{tribunalsWithData} <span style={{ fontSize: '1rem', color: 'var(--pico-muted-color)' }}>/ {snap?.tribunals_total || 96}</span></div>
              <p className="stat-label">Tribunais</p>
           </article>
           <article style={{ margin: 0 }}>
              <div className="stat-value text-warning">{snap?.total_items || 0}</div>
              <p className="stat-label">Itens no IA</p>
           </article>
        </div>
      </article>

      {/* Progress by Year — prefer snapshot data */}
      {Object.keys(snapshotByYear).length > 0 ? (
        <article>
          <header>
            <strong>ZIPs por Ano (Internet Archive)</strong>
          </header>
          <div className="grid" style={{ gap: '1rem' }}>
            {Object.entries(snapshotByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => (
                <div key={year} style={{ padding: '1rem', border: '1px solid var(--pico-muted-border-color)', borderRadius: 'var(--pico-border-radius)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <strong>{year}</strong>
                    <span className="text-primary" style={{ fontWeight: 'bold' }}>{(d as any).zip_count.toLocaleString()} ZIPs</span>
                  </div>
                  <div className="text-muted" style={{ fontSize: '0.875rem' }}>
                    Tribunais: {(d as any).tribunals_with_data} / {(d as any).tribunals_total}
                  </div>
                </div>
              ))}
          </div>
        </article>
      ) : progressByYear && Object.keys(progressByYear).length > 0 ? (
        <article>
          <header><strong>Progresso por Ano</strong></header>
          <div>
            {Object.entries(progressByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                const pct = (d as any).pct || 0;
                return (
                  <div key={year} style={{ marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <strong>{year}</strong>
                      <span>{pct.toFixed(1)}%</span>
                    </div>
                    <progress value={Math.round(Math.min(100, pct))} max="100"></progress>
                    <div className="text-muted" style={{ fontSize: '0.875rem', display: 'flex', gap: '1rem' }}>
                      <span>{(d as any).zips || 0} ZIPs</span>
                      <span>{(d as any).days_consolidated || 0} consolidados</span>
                      <span>{(d as any).unique_days || 0} / {(d as any).weekdays || 0} dias</span>
                    </div>
                  </div>
                );
              })}
          </div>
        </article>
      ) : null}

      {/* Tribunals by branch */}
      <div style={{ margin: '2rem 0' }}>
        <label htmlFor="tribunal-filter">Filtrar tribunais</label>
        <input
          id="tribunal-filter" type="search"
          value={query}
          onInput={(event) => setQuery((event.target as HTMLInputElement).value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setQuery('');
          }}
          placeholder="Busque por sigla ou nome (ex.: tjsp, trf1, stj)"
          aria-label="Filtrar tribunais por sigla ou nome"
          style={{ marginBottom: 0 }}
        />
      </div>

      {filteredGroups.length === 0 ? (
        <article>
          Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.
        </article>
      ) : filteredGroups.map(group => {
        return (
          <section key={group.name} style={{ marginBottom: '2rem' }}>
            <hgroup style={{ marginBottom: '1rem' }}>
              <h3>{group.name}</h3>
              <p>{group.tribunals.length} tribunais</p>
            </hgroup>
            <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))' }}>
              {group.tribunals.map(t => {
                let totalZips = 0;
                let latestDate = null;
                if (snapshotItems) {
                  for (const item of Object.values(snapshotItems)) {
                    if ((item as any).tribunal === t) {
                      totalZips += (item as any).zip_count;
                      if (!latestDate || (item as any).latest_date> latestDate) latestDate = (item as any).latest_date;
                    }
                  }
                }
                const hasData = totalZips> 0;

                return (
                  <a
                    key={t} href={`${baseUrl}publicacoes/${t.toLowerCase()}`}
                    style={{ textDecoration: 'none', color: 'inherit' }}>
                    <article style={{ padding: '1rem', marginBottom: '1rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong>{t}</strong>
                        {hasData && (
                          <span className="badge">{totalZips}</span>
                        )}
                      </div>
                      <div className="text-muted" style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                        {hasData ? `até ${latestDate}` : 'Sem dados'}
                      </div>
                    </article>
                  </a>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
