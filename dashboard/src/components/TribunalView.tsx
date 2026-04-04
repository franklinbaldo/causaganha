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
      <article style={{ marginBottom: 'var(--space-xl)' }}>
        <header style={{ borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 'var(--space-xs)' }}>
            <h2 style={{ margin: 0, fontSize: 'var(--font-size-2xl)' }}>Progresso do Arquivo</h2>
            {latestDate && (
              <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-content-tertiary)' }}>
                Última coleta: {latestDate}
                {snapshotAge && <span> · {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>}
              </span>
            )}
          </div>
        </header>

        {/* Quick Stats */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 'var(--space-md)',
          textAlign: 'center',
          padding: 'var(--space-md) 0'
        }}>
          <div>
            <div className="stat-value">{totalZips.toLocaleString()}</div>
            <p className="stat-label">ZIPs no IA</p>
          </div>
          <div>
            <div className="stat-value">{totalGB.toFixed(1)}<small style={{ fontSize: '0.4em', fontWeight: '500', marginLeft: '0.15em' }}>GB</small></div>
            <p className="stat-label">Volume</p>
          </div>
          <div>
            <div className="stat-value text-success">{tribunalsWithData}<small style={{ fontSize: '0.4em', fontWeight: '400', color: 'var(--color-content-tertiary)', marginLeft: '0.15em' }}>/ {snap?.tribunals_total || 96}</small></div>
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
        <article style={{ marginBottom: 'var(--space-xl)' }}>
          <header style={{ borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
            <strong>ZIPs por Ano</strong>
            <small style={{ float: 'right', color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)' }}>Internet Archive</small>
          </header>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--space-sm)' }}>
            {Object.entries(snapshotByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => (
                <div key={year} style={{
                  padding: 'var(--space-md)',
                  border: '1px solid var(--color-border-muted)',
                  borderRadius: 'var(--pico-border-radius)',
                  background: 'var(--color-surface)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 'var(--space-xs)' }}>
                    <strong style={{ fontSize: 'var(--font-size-sm)' }}>{year}</strong>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 'var(--font-size-sm)', fontWeight: '700' }}>{(d as any).zip_count.toLocaleString()}</span>
                  </div>
                  <small style={{ color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)' }}>
                    {(d as any).tribunals_with_data} / {(d as any).tribunals_total} tribunais
                  </small>
                </div>
              ))}
          </div>
        </article>
      ) : progressByYear && Object.keys(progressByYear).length > 0 ? (
        <article style={{ marginBottom: 'var(--space-xl)' }}>
          <header style={{ borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
            <strong>Progresso por Ano</strong>
          </header>
          <div>
            {Object.entries(progressByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                const pct = (d as any).pct || 0;
                return (
                  <div key={year} style={{ marginBottom: 'var(--space-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                      <strong style={{ fontSize: 'var(--font-size-sm)' }}>{year}</strong>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 'var(--font-size-sm)', fontWeight: '600' }}>{pct.toFixed(1)}%</span>
                    </div>
                    <progress value={Math.round(Math.min(100, pct))} max="100"></progress>
                    <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-content-tertiary)', display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-xs)' }}>
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
      <div style={{ margin: 'var(--space-lg) 0 var(--space-md)' }}>
        <label htmlFor="tribunal-filter" style={{ fontSize: 'var(--font-size-sm)', fontWeight: '500', color: 'var(--color-content-secondary)' }}>
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
          style={{ marginBottom: 0 }}
        />
      </div>

      {/* Tribunal Groups */}
      {filteredGroups.length === 0 ? (
        <article style={{ textAlign: 'center', padding: 'var(--space-xl)', color: 'var(--color-content-tertiary)' }}>
          Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.
        </article>
      ) : filteredGroups.map(group => {
        return (
          <section key={group.name} style={{ marginBottom: 'var(--space-xl)' }}>
            <div style={{ marginBottom: 'var(--space-md)', borderBottom: '1px solid var(--color-border-muted)', paddingBottom: 'var(--space-sm)' }}>
              <h3 style={{ fontSize: 'var(--font-size-lg)', marginBottom: '0.25rem' }}>{group.name}</h3>
              <small style={{ color: 'var(--color-content-tertiary)', fontSize: 'var(--font-size-xs)' }}>{group.tribunals.length} tribunais</small>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--space-sm)' }}>
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
                    <article style={{ padding: 'var(--space-md)', marginBottom: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <strong style={{ fontSize: 'var(--font-size-sm)' }}>{t}</strong>
                        {hasData && (
                          <span className="badge">{totalZips}</span>
                        )}
                      </div>
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-content-tertiary)', marginTop: 'var(--space-xs)' }}>
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
