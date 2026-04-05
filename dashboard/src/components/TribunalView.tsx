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
      <div className="card bg-base-100 shadow-sm border border-base-300 mb-16"><div className="card-body">
        <header className="pb-4 border-b border-base-300 mb-6">
          <div className="flex justify-between items-baseline flex-wrap gap-2 items-center">
            <h2 className="mb-0 text-2xl">Progresso do Arquivo</h2>
            {latestDate && (
              <span className="text-xs opacity-50">
                Última coleta: {latestDate}
                {snapshotAge && <span> · {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>}
              </span>
            )}
          </div>
        </header>

        {/* Quick Stats */}
        <div className="stats stats-vertical lg:stats-horizontal shadow-sm w-full mb-6">
          <div className="stat text-center">
            <div className="stat-value text-info">{totalZips.toLocaleString()}</div>
            <p className="stat-title mt-2">ZIPs no IA</p>
          </div>
          <div className="stat text-center">
            <div className="stat-value text-warning">{totalGB.toFixed(1)}<small className="font-medium" style={{ fontSize: '0.4em', marginLeft: '0.15em' }}>GB</small></div>
            <p className="stat-title mt-2">Volume</p>
          </div>
          <div className="stat text-center">
            <div className="stat-value text-success">{tribunalsWithData}<small className="font-normal opacity-50 text-base-content" style={{ fontSize: '0.4em', marginLeft: '0.15em' }}>/ {snap?.tribunals_total || 96}</small></div>
            <p className="stat-title mt-2">Tribunais</p>
          </div>
          <div className="stat text-center">
            <div className="stat-value text-primary">{snap?.total_items || 0}</div>
            <p className="stat-title mt-2">Itens no IA</p>
          </div>
        </div>
      </div></div>

      {/* Progress by Year */}
      {Object.keys(snapshotByYear).length > 0 ? (
        <div className="card bg-base-100 shadow-sm border border-base-300 mb-16"><div className="card-body">
          <header className="pb-4 border-b border-base-300 mb-6 flex justify-between items-baseline">
            <strong>ZIPs por Ano</strong>
            <small className="opacity-50 text-xs">Internet Archive</small>
          </header>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '1rem' }}>
            {Object.entries(snapshotByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => (
                <div className="card bg-base-100 shadow-sm border border-base-300 mb-0" key={year}><div className="card-body p-4">
                  <div className="flex justify-between items-baseline mb-2">
                    <strong className="text-sm">{year}</strong>
                    <span className="font-mono text-sm font-bold">{(d as any).zip_count.toLocaleString()}</span>
                  </div>
                  <small className="opacity-50 text-xs">
                    {(d as any).tribunals_with_data} / {(d as any).tribunals_total} tribunais
                  </small>
                </div></div>
              ))}
          </div>
        </div></div>
      ) : progressByYear && Object.keys(progressByYear).length > 0 ? (
        <div className="card bg-base-100 shadow-sm border border-base-300 mb-16"><div className="card-body">
          <header className="pb-4 border-b border-base-300 mb-6">
            <strong>Progresso por Ano</strong>
          </header>
          <div>
            {Object.entries(progressByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                const pct = (d as any).pct || 0;
                return (
                  <div key={year} className="mb-6">
                    <div className="flex justify-between items-baseline mb-2">
                      <strong className="text-sm">{year}</strong>
                      <span className="font-mono text-sm font-semibold">{pct.toFixed(1)}%</span>
                    </div>
                    <progress className="progress progress-primary" value={Math.round(Math.min(100, pct))} max="100" aria-label={`Progresso de coleta para o ano ${year}`}></progress>
                    <div className="opacity-50 text-xs flex gap-4 mt-2">
                      <span>{(d as any).zips || 0} ZIPs</span>
                      <span>{(d as any).days_consolidated || 0} consolidados</span>
                      <span>{(d as any).unique_days || 0} / {(d as any).weekdays || 0} dias</span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div></div>
      ) : null}

      {/* Tribunal Filter */}
      <div className="mb-6 mt-10">
        <label htmlFor="tribunal-filter" className="text-sm font-medium opacity-70 mb-2 block">
          Filtrar tribunais
        </label>
        <label className="input input-bordered flex items-center gap-2 max-w-lg">
          <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16" className="opacity-50"><path fillRule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clipRule="evenodd" /></svg>
          <input
            id="tribunal-filter" type="search"
            className="grow"
            value={query}
            onInput={(event) => setQuery((event.target as HTMLInputElement).value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') setQuery('');
            }}
            placeholder="Busque por sigla ou nome (ex.: tjsp, trf1, stj)"
            aria-label="Filtrar tribunais por sigla ou nome"
          />
          {query && <span className="badge badge-info badge-sm cursor-pointer" onClick={() => setQuery('')}>Limpar</span>}
        </label>
      </div>

      {/* Tribunal Groups */}
      {filteredGroups.length === 0 ? (
        <div className="empty-state">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
          <p className="mb-0">Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.</p>
        </div>
      ) : filteredGroups.map(group => {
        return (
          <section key={group.name} className="mb-16">
            <div className="mb-6 pb-4 border-b border-base-300">
              <h3 className="text-xl mb-2" style={{ marginBottom: '0.25rem' }}>{group.name}</h3>
              <small className="opacity-50 text-xs">{group.tribunals.length} tribunais</small>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '1rem' }}>
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
                    <div className="card bg-base-100 shadow-sm border border-base-300 mb-0 h-100"><div className="card-body p-4">
                      <div className="flex justify-between items-baseline items-center">
                        <strong className="text-sm">{t}</strong>
                        {hasData && (
                          <span className="badge">{totalZips}</span>
                        )}
                      </div>
                      <div className="text-xs opacity-50 mt-2">
                        {hasData ? `até ${latestDate}` : (
                          <span className="flex items-center gap-2" style={{ color: 'var(--color-warning)' }}>
                            <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                            Sem dados
                          </span>
                        )}
                      </div>
                    </div></div>
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
