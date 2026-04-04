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

  const snap = iaSnapshot?.summary;
  const totalZips = snap?.total_zips || pipeline?.total_zips || 0;
  const totalGB = snap?.total_size_gb || volume?.total_gb || 0;
  const tribunalsWithData = snap?.tribunals_with_data || 0;
  const latestDate = snap?.latest_collection_date;
  const snapshotAge = iaSnapshot?.generated_at;

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
      .filter(group => group.tribunals.length > 0);
  }, [normalizedQuery]);

  return (
    <div>
      {/* Archive Progress */}
      <article className="mb-xl">
        <header className="pb-sm border-bottom mb-md">
          <div className="flex-between flex-wrap gap-xs align-center">
            <h2 className="mb-0 text-2xl">Progresso do Arquivo</h2>
            {latestDate && (
              <span className="text-xs text-muted">
                Última coleta: {latestDate}
                {snapshotAge && <span> · {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>}
              </span>
            )}
          </div>
        </header>

        {/* Quick Stats */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
          gap: 'var(--space-md)',
          textAlign: 'center',
          padding: 'var(--space-md) 0'
        }}>
          <div>
            <div className="stat-value">{totalZips.toLocaleString()}</div>
            <p className="stat-label">ZIPs no IA</p>
          </div>
          <div>
            <div className="stat-value">{totalGB.toFixed(1)}<small className="font-medium" style={{ fontSize: '0.4em', marginLeft: '0.15em' }}>GB</small></div>
            <p className="stat-label">Volume</p>
          </div>
          <div>
            <div className="stat-value text-success">{tribunalsWithData}<small className="font-normal text-muted" style={{ fontSize: '0.4em', marginLeft: '0.15em' }}>/ {snap?.tribunals_total || 96}</small></div>
            <p className="stat-label">Tribunais</p>
          </div>
          <div>
            <div className="stat-value">{snap?.total_items || 0}</div>
            <p className="stat-label">Itens no IA</p>
          </div>
        </div>
      </article>

      {/* Progress by Year */}
      {Object.keys(snapshotByYear).length > 0 ? (
        <article className="mb-xl">
          <header className="pb-sm border-bottom mb-md flex-between">
            <strong>ZIPs por Ano</strong>
            <small className="text-muted text-xs">Internet Archive</small>
          </header>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 'var(--space-sm)' }}>
            {Object.entries(snapshotByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => (
                <article key={year} className="mb-0 p-md">
                  <div className="flex-between mb-xs">
                    <strong className="text-sm">{year}</strong>
                    <span className="font-mono text-sm font-bold">{(d as any).zip_count.toLocaleString()}</span>
                  </div>
                  <small className="text-muted text-xs">
                    {(d as any).tribunals_with_data} / {(d as any).tribunals_total} tribunais
                  </small>
                </article>
              ))}
          </div>
        </article>
      ) : progressByYear && Object.keys(progressByYear).length > 0 ? (
        <article className="mb-xl">
          <header className="pb-sm border-bottom mb-md">
            <strong>Progresso por Ano</strong>
          </header>
          <div>
            {Object.entries(progressByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                const pct = (d as any).pct || 0;
                return (
                  <div key={year} className="mb-md">
                    <div className="flex-between mb-xs">
                      <strong className="text-sm">{year}</strong>
                      <span className="font-mono text-sm font-semibold">{pct.toFixed(1)}%</span>
                    </div>
                    <progress value={Math.round(Math.min(100, pct))} max="100" aria-label={`Progresso de coleta para o ano ${year}`}></progress>
                    <div className="text-muted text-xs flex gap-sm mt-xs">
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

      {/* Tribunal Filter */}
      <div className="mb-md mt-lg">
        <label htmlFor="tribunal-filter" className="text-sm font-medium text-secondary">
          Filtrar tribunais
        </label>
        <input
          id="tribunal-filter" type="search"
          value={query}
          onInput={(event) => setQuery((event.target as HTMLInputElement).value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setQuery('');
          }}
          placeholder="Busque por sigla ou nome (ex.: tjsp, trf1, stj)"
          aria-label="Filtrar tribunais por sigla ou nome"
          className="mb-0"
        />
      </div>

      {/* Tribunal Groups */}
      {filteredGroups.length === 0 ? (
        <div className="empty-state">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <p className="mb-0">Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.</p>
        </div>
      ) : filteredGroups.map(group => {
        return (
          <section key={group.name} className="mb-xl">
            <div className="mb-md pb-sm border-bottom">
              <h3 className="text-lg mb-xs" style={{ marginBottom: '0.25rem' }}>{group.name}</h3>
              <small className="text-muted text-xs">{group.tribunals.length} tribunais</small>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 'var(--space-sm)' }}>
              {group.tribunals.map(t => {
                let totalZips = 0;
                let latestDate = null;
                if (snapshotItems) {
                  for (const item of Object.values(snapshotItems)) {
                    if ((item as any).tribunal === t) {
                      totalZips += (item as any).zip_count;
                      if (!latestDate || (item as any).latest_date > latestDate) latestDate = (item as any).latest_date;
                    }
                  }
                }
                const hasData = totalZips > 0;

                return (
                  <a
                    key={t} href={`${baseUrl}publicacoes/${t.toLowerCase()}`}
                    style={{ textDecoration: 'none', color: 'inherit' }}>
                    <article className="mb-0 p-md h-100">
                      <div className="flex-between align-center">
                        <strong className="text-sm">{t}</strong>
                        {hasData && (
                          <span className="badge">{totalZips}</span>
                        )}
                      </div>
                      <div className="text-xs text-muted mt-xs">
                        {hasData ? `até ${latestDate}` : (
                          <span className="flex align-center gap-xs" style={{ color: 'var(--color-warning)' }}>
                            <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                            Sem dados
                          </span>
                        )}
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
