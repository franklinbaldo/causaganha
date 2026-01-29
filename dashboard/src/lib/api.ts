import { API, ALL_TRIBUNALS } from './constants';
import type { IAMetadata, GHActionsResponse, DaySummary, TribunalStatus } from './types';
import { parseTribunalFromFilename, getFileStatus } from './utils';

const CACHE_KEY_PREFIX = 'causaganha_cache_';
const CACHE_TTL_HISTORICAL = 24 * 60 * 60 * 1000; // 24 hours
const CACHE_TTL_TODAY = 5 * 60 * 1000; // 5 minutes

// Pre-built cache URL (generated during dashboard deployment)
const STATIC_CACHE_URL = '/causaganha/cache/';

// Types for pre-built cache
export interface PreBuiltCache {
    meta: { version: string; generated_at: string };
    today: {
        date: string;
        files_today: number;
        size_today: number;
        tribunal_status: Record<string, { status: string; size?: number }>;
        days_archived: number;
        health: number;
    };
    runs: {
        runs: Array<{
            id: number;
            name: string;
            run_number: number;
            status: string;
            conclusion: string | null;
            created_at: string;
            html_url: string;
        }>;
        health: number;
    };
    calendar: {
        days: Record<string, { size: number; tribunal_count: number; exists: boolean; level: number }>;
        stats: { total_size: number; days_with_data: number };
    };
}

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

/**
 * Get cached data if valid
 */
function getFromCache<T>(key: string, ttl: number): T | null {
    try {
        const raw = localStorage.getItem(CACHE_KEY_PREFIX + key);
        if (!raw) return null;

        const entry: CacheEntry<T> = JSON.parse(raw);
        if (Date.now() - entry.timestamp > ttl) {
            localStorage.removeItem(CACHE_KEY_PREFIX + key);
            return null;
        }

        return entry.data;
    } catch {
        return null;
    }
}

/**
 * Save data to cache
 */
function saveToCache<T>(key: string, data: T): void {
    try {
        const entry: CacheEntry<T> = { data, timestamp: Date.now() };
        localStorage.setItem(CACHE_KEY_PREFIX + key, JSON.stringify(entry));
    } catch {
        // localStorage might be full or unavailable
    }
}

/**
 * Fetch Internet Archive metadata for a specific date
 */
export async function fetchIAMetadata(date: string): Promise<IAMetadata | null> {
    const isToday = date === new Date().toISOString().split('T')[0];
    const ttl = isToday ? CACHE_TTL_TODAY : CACHE_TTL_HISTORICAL;

    // Check cache first
    const cached = getFromCache<IAMetadata>(`ia_${date}`, ttl);
    if (cached) return cached;

    try {
        const response = await fetch(API.IA_METADATA(date));
        if (!response.ok) {
            if (response.status === 404) return null;
            throw new Error(`HTTP ${response.status}`);
        }

        const data: IAMetadata = await response.json();
        saveToCache(`ia_${date}`, data);
        return data;
    } catch (error) {
        console.error(`Failed to fetch IA metadata for ${date}:`, error);
        return null;
    }
}

/**
 * Parse IA metadata into DaySummary
 */
export function parseIAMetadata(date: string, metadata: IAMetadata | null): DaySummary {
    if (!metadata || !metadata.files) {
        return {
            date,
            itemSize: 0,
            tribunalCount: 0,
            tribunals: [],
            exists: false,
        };
    }

    const tribunalStatuses: TribunalStatus[] = [];
    const seenTribunals = new Set<string>();

    // Parse files to get tribunal statuses
    for (const file of metadata.files) {
        const tribunal = parseTribunalFromFilename(file.name);
        const status = getFileStatus(file.name);

        if (tribunal && status) {
            seenTribunals.add(tribunal);
            tribunalStatuses.push({
                tribunal,
                status,
                size: status === 'ok' ? parseInt(file.size, 10) : undefined,
                fileCount: file.filecount ? parseInt(file.filecount, 10) : undefined,
            });
        }
    }

    // Add pending status for missing tribunals
    for (const tribunal of ALL_TRIBUNALS) {
        if (!seenTribunals.has(tribunal)) {
            tribunalStatuses.push({
                tribunal,
                status: 'pending',
            });
        }
    }

    const zipCount = tribunalStatuses.filter(t => t.status === 'ok').length;

    return {
        date,
        itemSize: metadata.item_size || 0,
        tribunalCount: zipCount,
        tribunals: tribunalStatuses,
        exists: true,
    };
}

/**
 * Fetch GitHub Actions workflow runs
 */
export async function fetchGHRuns(): Promise<GHActionsResponse | null> {
    try {
        const response = await fetch(API.GH_RUNS);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to fetch GitHub Actions runs:', error);
        return null;
    }
}

/**
 * Fetch data for multiple dates (for calendar)
 */
export async function fetchMultipleDates(dates: string[]): Promise<Map<string, DaySummary>> {
    const results = new Map<string, DaySummary>();

    // Fetch in batches to avoid overwhelming the API
    const batchSize = 5;
    for (let i = 0; i < dates.length; i += batchSize) {
        const batch = dates.slice(i, i + batchSize);
        const promises = batch.map(async (date) => {
            const metadata = await fetchIAMetadata(date);
            return { date, summary: parseIAMetadata(date, metadata) };
        });

        const batchResults = await Promise.all(promises);
        for (const { date, summary } of batchResults) {
            results.set(date, summary);
        }
    }

    return results;
}

/**
 * Fetch pre-built cache (generated during dashboard deployment)
 * Served directly from GitHub Pages for fast loading
 */
export async function fetchPreBuiltCache(): Promise<PreBuiltCache | null> {
    const CACHE_KEY = 'prebuilt_cache';
    const CACHE_TTL = 60 * 1000; // 1 minute - short since we want fresh data

    // Check localStorage first for recently fetched cache
    const cached = getFromCache<PreBuiltCache>(CACHE_KEY, CACHE_TTL);
    if (cached) {
        console.log('[Cache] Using localStorage pre-built cache');
        return cached;
    }

    // Load cache from GitHub Pages (generated during deploy)
    try {
        const response = await fetch(`${STATIC_CACHE_URL}today.json`, { cache: 'no-cache' });
        if (response.ok) {
            // Load all cache parts in parallel
            const [todayRes, runsRes, calendarRes, metaRes] = await Promise.all([
                response.json(),
                fetch(`${STATIC_CACHE_URL}runs.json`, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null),
                fetch(`${STATIC_CACHE_URL}calendar.json`, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null),
                fetch(`${STATIC_CACHE_URL}meta.json`, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null),
            ]);

            const cache: PreBuiltCache = {
                meta: metaRes || { version: '2.0', generated_at: new Date().toISOString() },
                today: todayRes,
                runs: runsRes || { runs: [], health: 0 },
                calendar: calendarRes || { days: {}, stats: { total_size: 0, days_with_data: 0 } },
            };

            console.log('[Cache] Loaded from static files');
            saveToCache(CACHE_KEY, cache);
            return cache;
        }
    } catch (error) {
        console.log('[Cache] Static cache not available:', error);
    }

    return null;
}

/**
 * Get cache age in human-readable format
 */
export function getCacheAge(generatedAt: string): string {
    const generated = new Date(generatedAt);
    const now = new Date();
    const diffMs = now.getTime() - generated.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'agora';
    if (diffMins < 60) return `há ${diffMins}min`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `há ${diffHours}h`;
    const diffDays = Math.floor(diffHours / 24);
    return `há ${diffDays}d`;
}
