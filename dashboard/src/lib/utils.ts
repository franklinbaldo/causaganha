/**
 * Format bytes to human-readable string
 */
export function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Format relative time (e.g., "5min", "2h", "1d")
 */
export function timeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'agora';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}min`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
}

/**
 * Format date as YYYY-MM-DD
 */
export function formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
}

/**
 * Get today's date in YYYY-MM-DD format
 */
export function getToday(): string {
    return formatDate(new Date());
}

/**
 * Get date N days ago in YYYY-MM-DD format
 */
export function getDaysAgo(n: number): string {
    const date = new Date();
    date.setDate(date.getDate() - n);
    return formatDate(date);
}

/**
 * Parse tribunal code from filename
 * e.g., "djen-2026-01-28-TJSP.zip" -> "TJSP"
 */
export function parseTribunalFromFilename(filename: string): string | null {
    const match = filename.match(/djen-\d{4}-\d{2}-\d{2}-([A-Z0-9]+)\.(zip|absent)$/);
    return match ? match[1] : null;
}

/**
 * Determine file status from filename
 */
export function getFileStatus(filename: string): 'ok' | 'absent' | null {
    if (filename.endsWith('.zip')) return 'ok';
    if (filename.endsWith('.absent')) return 'absent';
    return null;
}

/**
 * Calculate calendar level based on size relative to max
 */
export function getCalendarLevel(size: number, maxSize: number): 0 | 1 | 2 | 3 | 4 {
    if (size === 0 || maxSize === 0) return 0;
    const ratio = size / maxSize;
    if (ratio >= 0.76) return 4;
    if (ratio >= 0.51) return 3;
    if (ratio >= 0.26) return 2;
    if (ratio > 0) return 1;
    return 0;
}

/**
 * Calculate pipeline health percentage from workflow runs
 */
export function calculateHealth(runs: { conclusion: string | null }[]): number {
    if (runs.length === 0) return 0;
    const successful = runs.filter(r => r.conclusion === 'success').length;
    return Math.round((successful / runs.length) * 100);
}

/**
 * Get health status based on percentage
 */
export function getHealthStatus(health: number): 'operational' | 'degraded' | 'failure' {
    if (health >= 80) return 'operational';
    if (health >= 50) return 'degraded';
    return 'failure';
}

/**
 * Generate an array of dates for the calendar (last N weeks)
 */
export function generateCalendarDates(weeks: number): string[] {
    const dates: string[] = [];
    const today = new Date();
    const totalDays = weeks * 7;

    // Start from the beginning of the week (Monday)
    const startDate = new Date(today);
    startDate.setDate(today.getDate() - totalDays + 1);

    // Adjust to Monday
    const dayOfWeek = startDate.getDay();
    const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
    startDate.setDate(startDate.getDate() - daysToMonday);

    for (let i = 0; i < totalDays; i++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + i);
        dates.push(formatDate(date));
    }

    return dates;
}

/**
 * Chunk an array into groups of size n
 */
export function chunk<T>(arr: T[], n: number): T[][] {
    const result: T[][] = [];
    for (let i = 0; i < arr.length; i += n) {
        result.push(arr.slice(i, i + n));
    }
    return result;
}
