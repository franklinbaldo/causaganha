/**
 * Per-tribunal partitioning of the tribunal_calendar contract (#1191).
 *
 * TribunalCoverageExplorer (client:only) used to receive the entire
 * tribunal_calendar contract (~13.9MB, every tribunal × date in the archive)
 * as a serialized island prop, even though the drill-down UI only ever
 * renders one tribunal at a time — client:only still serializes its props
 * into the page for hydration, so that shipped the whole archive to every
 * /stats visitor. This module partitions the same canonical contract by
 * tribunal (no second source of truth) so a build step can write one small
 * JSON file per tribunal and the client can fetch only the one it needs,
 * following the filter-at-build-time pattern already used by
 * web/src/pages/publicacoes/[tribunal].astro.
 */
import { tribunalCalendarSchema } from './data/contracts';
import type { TribunalCalendarRow } from './tribunalCoverageDrilldown';

/** Groups rows by tribunal, preserving each row's shape and relative order. */
export function partitionByTribunal(
  rows: TribunalCalendarRow[],
): Map<string, TribunalCalendarRow[]> {
  const byTribunal = new Map<string, TribunalCalendarRow[]>();
  for (const row of rows) {
    const bucket = byTribunal.get(row.tribunal);
    if (bucket) bucket.push(row);
    else byTribunal.set(row.tribunal, [row]);
  }
  return byTribunal;
}

/** Relative (under public/) path of one tribunal's partition file. */
export function tribunalCalendarPartitionPath(tribunal: string): string {
  return `data/tribunal_calendar_by_tribunal/${tribunal.toLowerCase()}.json`;
}

/**
 * Client-side loader for one tribunal's partition. Resolves against
 * publicBase exactly like loadContractClient (web/src/lib/data/index.ts) —
 * never a bare "/data/..." absolute path, which would ignore a non-root
 * `base`. Any failure (HTTP, network, malformed JSON, schema violation)
 * returns null rather than throwing — the caller renders a load-error state.
 */
export async function loadTribunalCalendarPartition(
  tribunal: string,
  publicBase: string,
): Promise<TribunalCalendarRow[] | null> {
  const base = publicBase.endsWith('/') ? publicBase : publicBase + '/';
  const url = base + tribunalCalendarPartitionPath(tribunal);
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const json: unknown = await res.json();
    const parsed = tribunalCalendarSchema.safeParse(json);
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}
