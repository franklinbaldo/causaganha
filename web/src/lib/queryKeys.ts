export const QUERY_KEYS = {
  iaCoverage:    (year: number) => ['ia-coverage', year] as const,
  djenSearch:    (query: Record<string, unknown>) => ['djen-search', query] as const,
} as const;
