/**
 * Single-request fetcher for Internet Archive coverage data.
 * Uses the IA Advanced Search API to get all tribunal items for a year
 * in ONE HTTP call instead of 91 individual metadata requests.
 */

import { TRIBUNAIS } from './tribunais';
import { fetchWithRetry } from './fetchData';

const CACHE_TTL_MS = 30 * 60 * 1000; // 30 minutes

// IA system files per item (approximate): _meta.xml, _files.xml,
// _meta.sqlite, _archive.torrent, __ia_thumb.jpg
const IA_SYSTEM_FILES = 5;

export interface TribunalMetadata {
  tribunal: string;
  fileCount: number;
  expectedDays: number;
  percentage: number;
  notFound: boolean;
  error: string | null;
}

interface CacheEntry {
  timestamp: number;
  data: TribunalMetadata[];
}

function isLeapYear(year: number): boolean {
  return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
}

export function getExpectedDays(year: number): number {
  const now = new Date();
  const currentYear = now.getFullYear();
  if (year < currentYear) {
    return isLeapYear(year) ? 366 : 365;
  }
  if (year > currentYear) return 0;
  // Current year: days elapsed from Jan 1 to today (inclusive)
  const jan1 = new Date(year, 0, 1);
  const diffMs = now.getTime() - jan1.getTime();
  return Math.floor(diffMs / 86400000) + 1;
}

function getCacheKey(year: number): string {
  return `cg-annual-coverage-${year}`;
}

function readCache(year: number): TribunalMetadata[] | null {
  try {
    const raw = sessionStorage.getItem(getCacheKey(year));
    if (!raw) return null;
    const cached: CacheEntry = JSON.parse(raw);
    if (Date.now() - cached.timestamp > CACHE_TTL_MS) {
      sessionStorage.removeItem(getCacheKey(year));
      return null;
    }
    return cached.data;
  } catch {
    return null;
  }
}

function writeCache(year: number, data: TribunalMetadata[]): void {
  try {
    sessionStorage.setItem(getCacheKey(year), JSON.stringify({
      timestamp: Date.now(),
      data,
    }));
  } catch { /* quota exceeded — ignore */ }
}

export function clearCache(year: number): void {
  try {
    sessionStorage.removeItem(getCacheKey(year));
  } catch { /* ignore */ }
}

/**
 * Extract tribunal code from an IA item identifier.
 * "djen-tjsp-2026" -> "TJSP"
 * "djen-tre-ac-2026" -> "TRE-AC"
 */
function tribunalFromItemId(identifier: string, year: number): string | null {
  const prefix = 'djen-';
  const suffix = `-${year}`;
  if (!identifier.startsWith(prefix) || !identifier.endsWith(suffix)) return null;
  const middle = identifier.slice(prefix.length, -suffix.length);
  return middle.toUpperCase();
}

export type OnProgressCallback = (done: number, total: number, results: TribunalMetadata[]) => void;

export interface FetchOptions {
  useCache?: boolean;
  tribunals?: string[];
}

/**
 * Fetch coverage for all tribunals in a single HTTP call using IA Advanced Search.
 *
 * @param year - Year to check (e.g. 2026)
 * @param onProgress - Callback(done, total, results) — called once when done
 * @param options - { useCache: true, tribunals: TRIBUNAIS }
 * @returns Array of TribunalMetadata
 */
export async function fetchAllTribunalMetadata(
  year: number,
  onProgress: OnProgressCallback | undefined,
  options: FetchOptions = {}
): Promise<TribunalMetadata[]> {
  const { useCache = true, tribunals = TRIBUNAIS } = options;

  if (useCache) {
    const cached = readCache(year);
    if (cached) {
      onProgress?.(cached.length, cached.length, cached);
      return cached;
    }
  }

  const expectedDays = getExpectedDays(year);

  // Single API call: get all djen-*-{year} items with their file counts
  const searchUrl = `https://archive.org/advancedsearch.php?q=identifier:djen-*-${year}&fl[]=identifier&fl[]=files_count&rows=200&output=json`;

  let iaDocs: { identifier: string; files_count?: number }[] = [];
  let fetchError: string | null = null;

  try {
    const res = await fetchWithRetry(searchUrl, {}, 3);
    if (res.ok) {
      const data = await res.json();
      iaDocs = data?.response?.docs || [];
    } else {
      fetchError = `HTTP ${res.status}`;
    }
  } catch (err: unknown) {
    fetchError = (err instanceof Error ? err.message : null) || 'Fetch failed';
  }

  // Build a map of tribunal -> files_count from IA response
  const iaMap = new Map<string, number>();
  for (const doc of iaDocs) {
    const tribunal = tribunalFromItemId(doc.identifier, year);
    if (tribunal) {
      const rawCount = doc.files_count || 0;
      // Subtract IA system files to approximate actual data file count
      const fileCount = Math.max(0, rawCount - IA_SYSTEM_FILES);
      iaMap.set(tribunal, fileCount);
    }
  }

  // Build results for all tribunals (including those not found in IA)
  const results: TribunalMetadata[] = tribunals.map(tribunal => {
    const fileCount = iaMap.get(tribunal) ?? 0;
    const notFound = !iaMap.has(tribunal);
    const percentage = expectedDays > 0
      ? Math.min(100, (fileCount / expectedDays) * 100)
      : 0;
    return {
      tribunal,
      fileCount,
      expectedDays,
      percentage,
      notFound,
      error: fetchError,
    };
  });

  onProgress?.(results.length, results.length, results);

  if (useCache && !fetchError) {
    writeCache(year, results);
  }

  return results;
}
