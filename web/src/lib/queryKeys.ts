export const QUERY_KEYS = {
  dashboard:     ['dashboard']          as const,
  dashboardMeta: ['dashboard', 'meta'] as const,
  iaCoverage:    (year: number) => ['ia-coverage', year] as const,
  djenSearch:    (query: Record<string, unknown>) => ['djen-search', query] as const,
  pipelineRuns:  ['pipeline', 'runs']   as const,
  pipelineToday: ['pipeline', 'today']  as const,
} as const;
