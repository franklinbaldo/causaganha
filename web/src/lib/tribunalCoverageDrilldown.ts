/**
 * Pure logic for the /stats tribunal+period drill-down (#1131).
 *
 * Backed strictly by the tribunal_calendar contract, which only proves
 * `uploaded`/`absent` per (tribunal, date). A day absent from the contract
 * is `sem_evidencia` — never inferred as `absent` or folded into 0%.
 */

export interface TribunalCalendarRow {
  tribunal: string;
  date: string;
  status: 'uploaded' | 'absent';
}

export type DailyStatus = 'uploaded' | 'absent' | 'sem_evidencia';

export interface DailyState {
  date: string;
  status: DailyStatus;
}

export interface DrilldownSummary {
  uploaded: number;
  absent: number;
  semEvidencia: number;
  totalDays: number;
  coveragePct: number | null;
}

export interface DrilldownState {
  tribunal: string;
  start: string;
  end: string;
}

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

function isValidIsoDate(value: string): boolean {
  if (!ISO_DATE_RE.test(value)) return false;
  const d = new Date(value + 'T00:00:00Z');
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === value;
}

/** Classifies each day in [startIso, endIso] as uploaded, absent, or sem_evidencia for one tribunal. */
export function buildDailyStates(
  rows: TribunalCalendarRow[],
  tribunal: string,
  startIso: string,
  endIso: string
): DailyState[] {
  const byDate = new Map<string, DailyStatus>();
  for (const row of rows) {
    if (row.tribunal === tribunal) byDate.set(row.date, row.status);
  }

  const states: DailyState[] = [];
  let cursor = new Date(startIso + 'T00:00:00Z');
  const end = new Date(endIso + 'T00:00:00Z');
  while (cursor.getTime() <= end.getTime()) {
    const iso = cursor.toISOString().slice(0, 10);
    states.push({ date: iso, status: byDate.get(iso) ?? 'sem_evidencia' });
    cursor = new Date(cursor.getTime() + 24 * 60 * 60 * 1000);
  }
  return states;
}

/** Summarizes daily states; coveragePct is null (never 0) when no day is observed. */
export function summarizeDailyStates(states: DailyState[]): DrilldownSummary {
  let uploaded = 0;
  let absent = 0;
  let semEvidencia = 0;
  for (const state of states) {
    if (state.status === 'uploaded') uploaded++;
    else if (state.status === 'absent') absent++;
    else semEvidencia++;
  }
  const observed = uploaded + absent;
  return {
    uploaded,
    absent,
    semEvidencia,
    totalDays: states.length,
    coveragePct: observed > 0 ? Math.round((uploaded / observed) * 1000) / 10 : null,
  };
}

/** Parses tribunal/start/end from a querystring, falling back to defaults on unknown/malformed values. */
export function parseDrilldownQuery(
  params: URLSearchParams,
  knownTribunals: string[],
  defaults: DrilldownState
): DrilldownState {
  const tribunalParam = params.get('tribunal');
  const startParam = params.get('start');
  const endParam = params.get('end');

  const tribunal = tribunalParam && knownTribunals.includes(tribunalParam) ? tribunalParam : defaults.tribunal;
  const start = startParam && isValidIsoDate(startParam) ? startParam : defaults.start;
  const end = endParam && isValidIsoDate(endParam) ? endParam : defaults.end;

  return { tribunal, start, end };
}

/** Serializes drill-down state into a querystring, inverse of parseDrilldownQuery. */
export function buildDrilldownQuery(state: DrilldownState): URLSearchParams {
  return new URLSearchParams({ tribunal: state.tribunal, start: state.start, end: state.end });
}
