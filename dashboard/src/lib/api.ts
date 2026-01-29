import { API, ALL_TRIBUNALS } from './constants';
import type { IAMetadata, GHActionsResponse, DaySummary, TribunalStatus } from './types';
import { parseTribunalFromFilename, getFileStatus } from './utils';

const CACHE_KEY_PREFIX = 'causaganha_cache_';
const CACHE_TTL_HISTORICAL = 24 * 60 * 60 * 1000; // 24 hours
const CACHE_TTL_TODAY = 5 * 60 * 1000; // 5 minutes

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
