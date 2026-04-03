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
        <div>
          <div>
            <h2>Progresso do Arquivo</h2>
            <p>
              {totalZips.toLocaleString()} ZIPs no Internet Archive
            </p>
            {latestDate && (
              <p>
                Ultima coleta: {latestDate}
                {snapshotAge && <span>| Instantaneo: {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>}
              </p>
            )}
          </div>

          <div>
            <span className="text-accent">{tribunalsWithData}</span>
            <span>Tribunais com dados</span>
          </div>
        </div>

        {/* Quick Stats Grid */}
        <div className="grid">
           <div>
              <small>ZIPs no IA</small>
              <span className="text-accent">
                {totalZips.toLocaleString()}
              </span>
           </div>
           <div>
              <small>Volume</small>
              <span>
                {totalGB.toFixed(1)} GB
              </span>
           </div>
           <div>
              <small>Tribunais</small>
              <span className="text-success">
                {tribunalsWithData} / {snap?.tribunals_total || 96}
              </span>
           </div>
           <div>
              <small>Itens no IA</small>
              <span className="text-warning">
                {snap?.total_items || 0}
              </span>
           </div>
        </div>

      </article>

      {/* Progress by Year — prefer snapshot data */}
      {Object.keys(snapshotByYear).length> 0 ? (
        <article>
          <h3>ZIPs por Ano (Internet Archive)</h3>
          <div>
            {Object.entries(snapshotByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                return (
                  <div key={year}>
                    <div>
                      <span>{year}</span>
                      <span className="text-accent">{d.zip_count.toLocaleString()} ZIPs</span>
                    </div>
                    <div>
                      <small>{d.tribunals_with_data} / {d.tribunals_total} tribunais</small>
                    </div>
                  </div>
                );
              })}
          </div>
        </article>
      ) : progressByYear && Object.keys(progressByYear).length> 0 ? (
        <article>
          <h3>Progresso por Ano</h3>
          <div>
            {Object.entries(progressByYear)
              .sort(([a], [b]) => b.localeCompare(a))
              .map(([year, d]) => {
                const pct = d.pct || 0;
                const progressStatus =
                  pct>= 80 ? 'high coverage' :
                  pct>= 30 ? 'partial coverage' :
                  pct> 0 ? 'low coverage' :
                  'no coverage';
                return (
                  <div key={year}>
                    <div>
                      <span>{year}</span>
                      <span>{pct.toFixed(1)}% ({progressStatus})</span>
                    </div>
                    <div
                      role="progressbar" aria-valuenow={Math.round(Math.min(100, pct))}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`Progresso do ano ${year}: ${pct.toFixed(1)}%, ${progressStatus}.`}>
                      <div
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                    <div>
                      <small>{d.zips || 0} ZIPs</small>
                      <small>{d.days_consolidated || 0} consolidados</small>
                      <small>{d.unique_days || 0} / {d.weekdays || 0} dias</small>
                    </div>
                  </div>
                );
              })}
          </div>
        </article>
      ) : null}

      {/* Tribunals by branch */}
      <div>
        <label
          htmlFor="tribunal-filter">
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
        />
      </div>

      {filteredGroups.length === 0 ? (
        <article>
          Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.
        </article>
      ) : filteredGroups.map(group => {
        // Count group totals from snapshot
        return (
          <div key={group.name}>
            <div>
              <h3>{group.name}</h3>
              <small>{group.tribunals.length} tribunais</small>
            </div>
            <div className="grid">
              {group.tribunals.map(t => {
                let totalZips = 0;
                let latestDate = null;
                if (snapshotItems) {
                  for (const item of Object.values(snapshotItems)) {
                    if (item.tribunal === t) {
                      totalZips += item.zip_count;
                      if (!latestDate || item.latest_date> latestDate) latestDate = item.latest_date;
                    }
                  }
                }
                const hasData = totalZips> 0;

                return (
                  <a
                    key={t} href={`${baseUrl}publicacoes/${t.toLowerCase()}`}>
                    <article>
                      <div>
                        <span>{t}</span>
                        {hasData && (
                          <span className="text-accent">{totalZips}</span>
                        )}
                      </div>
                      {hasData ? (
                        <small>ate {latestDate}</small>
                      ) : (
                        <small>—</small>
                      )}
                    </article>
                  </a>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
