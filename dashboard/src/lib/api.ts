import type { GHWorkflowRun, TribunalStatus } from './types';

const CACHE_KEY_PREFIX = 'causaganha_cache_';
const CACHE_TTL = 60 * 1000; // 1 minute

// Pre-built cache URL (generated from catalog manifest during deploy/pipeline)
const STATIC_CACHE_URL = '/causaganha/cache/';

// --- Cache types (match generate_dashboard_cache.py output) ---

export interface CacheMeta {
    version: string;
    generated_at: string;
    source: string;
    manifest_available?: boolean;
}

export interface StepRunStats {
    success: boolean;
    stats: Record<string, string>;
}

export interface LastRunStats {
    generated_at: string;
    job: string;
    steps: Record<string, StepRunStats>;
}

export interface PipelineMetrics {
    total_zips: number;
    days_consolidated: number;
    total_parquets: number;
    dates_collected: number;
    backfill_total: number;
    backfill_done: number;
    progress_pct: number;
}

export interface CacheToday {
    date: string;
    files_today: number;
    size_today: number;
    tribunal_status: Record<string, { status: string; size?: number | null }>;
    days_archived: number;
    health: number;
    pipeline?: PipelineMetrics;
    last_run?: LastRunStats;
}

export interface CacheRuns {
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
}

export interface CacheCalendar {
    days: Record<string, { size: number; tribunal_count: number; exists: boolean; level: number }>;
    stats: { total_size: number; days_with_data: number; biggest_day: string | null; biggest_size: number };
}

export interface DashboardCache {
    meta: CacheMeta;
    today: CacheToday;
    runs: CacheRuns;
    calendar: CacheCalendar;
}

// --- localStorage cache layer ---

interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

function getFromLocalStorage<T>(key: string): T | null {
    try {
        const raw = localStorage.getItem(CACHE_KEY_PREFIX + key);
        if (!raw) return null;
        const entry: CacheEntry<T> = JSON.parse(raw);
        if (Date.now() - entry.timestamp > CACHE_TTL) {
            localStorage.removeItem(CACHE_KEY_PREFIX + key);
            return null;
        }
        return entry.data;
    } catch {
        return null;
    }
}

function saveToLocalStorage<T>(key: string, data: T): void {
    try {
        const entry: CacheEntry<T> = { data, timestamp: Date.now() };
        localStorage.setItem(CACHE_KEY_PREFIX + key, JSON.stringify(entry));
    } catch {
        // localStorage might be full or unavailable
    }
}

// --- Public API ---

/**
 * Fetch the full dashboard cache (all data from static JSON files).
 * This is the single data source for all dashboard components.
 */
export async function fetchDashboardCache(): Promise<DashboardCache | null> {
    const CACHE_KEY = 'dashboard_cache';

    // Check localStorage first
    const cached = getFromLocalStorage<DashboardCache>(CACHE_KEY);
    if (cached) return cached;

    // Fetch all cache files in parallel from GitHub Pages
    try {
        const [todayRes, runsRes, calendarRes, metaRes] = await Promise.all([
            fetch(`${STATIC_CACHE_URL}today.json`, { cache: 'no-cache' }),
            fetch(`${STATIC_CACHE_URL}runs.json`, { cache: 'no-cache' }),
            fetch(`${STATIC_CACHE_URL}calendar.json`, { cache: 'no-cache' }),
            fetch(`${STATIC_CACHE_URL}meta.json`, { cache: 'no-cache' }),
        ]);

        if (!todayRes.ok) return null;

        const [today, runs, calendar, meta] = await Promise.all([
            todayRes.json(),
            runsRes.ok ? runsRes.json() : { runs: [], health: 0 },
            calendarRes.ok ? calendarRes.json() : { days: {}, stats: { total_size: 0, days_with_data: 0, biggest_day: null, biggest_size: 0 } },
            metaRes.ok ? metaRes.json() : { version: '3.0', generated_at: new Date().toISOString(), source: 'unknown' },
        ]);

        const cache: DashboardCache = { meta, today, runs, calendar };
        saveToLocalStorage(CACHE_KEY, cache);
        return cache;
    } catch (error) {
        console.error('[Cache] Failed to load:', error);
        return null;
    }
}

/**
 * Extract tribunal status for TribunalHeatmap from cache.
 */
export function extractTribunalStatus(cache: DashboardCache): {
    date: string;
    status: Record<string, TribunalStatus>;
} {
    const statusMap: Record<string, TribunalStatus> = {};
    for (const [tribunal, info] of Object.entries(cache.today.tribunal_status)) {
        statusMap[tribunal] = {
            tribunal,
            status: info.status as TribunalStatus['status'],
            size: info.size ?? undefined,
        };
    }
    return { date: cache.today.date, status: statusMap };
}

/**
 * Extract recent days for RecentDays from cache.
 */
export function extractRecentDays(cache: DashboardCache, count: number = 5): Array<{
    date: string;
    size: number;
    tribunalCount: number;
    exists: boolean;
}> {
    const days = Object.entries(cache.calendar.days)
        .sort(([a], [b]) => b.localeCompare(a))
        .slice(0, count)
        .map(([date, data]) => ({
            date,
            size: data.size,
            tribunalCount: data.tribunal_count,
            exists: data.exists,
        }));
    return days;
}

/**
 * Extract workflow runs for RecentRuns from cache.
 */
export function extractRuns(cache: DashboardCache): GHWorkflowRun[] {
    return cache.runs.runs.map(r => ({
        id: r.id,
        name: r.name,
        run_number: r.run_number,
        status: r.status as GHWorkflowRun['status'],
        conclusion: r.conclusion as GHWorkflowRun['conclusion'],
        created_at: r.created_at,
        html_url: r.html_url,
        display_title: r.name,
    }));
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
