/**
 * Stats processing logic shared between stats.astro and the BDD step file.
 * This ensures the test validates the same logic the page actually uses.
 */

export interface CompletedItem {
  tribunal_count?: number;
  tribunais_coletados?: string[];
  tribunais_ausentes?: string[];
}

export interface CourtStat {
  court: string;
  rate: number;
  total: number;
  collected: number;
  absent: number;
}

export interface WeeklyAverage {
  dayIdx: number;
  name: string;
  avg: number;
  avgPct: number;
  daysCount: number;
}

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

/**
 * Parse a date key that may be prefixed with "djen-" (as stored in the catalog)
 * or be a plain YYYY-MM-DD string.
 */
function parseDateKey(dateStr: string): Date | null {
  const cleaned = dateStr.replace('djen-', '');
  const parts = cleaned.split('-');
  if (parts.length !== 3) return null;
  const d = new Date(Date.UTC(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2])));
  return isNaN(d.getTime()) ? null : d;
}

export function processCoverageOverview(
  data: Record<string, CompletedItem>,
  recentDays = 30
): {
  avgPct: number;
  avgCoverage: number;
  bestDay: string | null;
  bestCount: number;
  worstDay: string | null;
  worstCount: number;
} {
  const sortedDates = Object.keys(data).sort((a, b) => b.localeCompare(a));
  const recent = sortedDates.slice(0, recentDays);

  let totalCoverage = 0;
  let bestDay: string | null = null;
  let worstDay: string | null = null;
  let bestCount = -1;
  let worstCount = 999;

  for (const date of recent) {
    const count = data[date].tribunal_count || 0;
    totalCoverage += count;
    if (count > bestCount) { bestCount = count; bestDay = date; }
    if (count < worstCount) { worstCount = count; worstDay = date; }
  }

  const avgCoverage = recent.length > 0 ? totalCoverage / recent.length : 0;
  const avgPct = (avgCoverage / 91) * 100;

  return { avgPct, avgCoverage, bestDay, bestCount, worstDay, worstCount };
}

export function processCourtReliability(
  data: Record<string, CompletedItem>
): { top5: CourtStat[]; bottom5: CourtStat[] } {
  const sortedDates = Object.keys(data).sort((a, b) => b.localeCompare(a));
  const courtStats: Record<string, { collected: number; absent: number }> = {};

  for (const date of sortedDates) {
    const item = data[date];
    for (const c of (item.tribunais_coletados || [])) {
      if (!courtStats[c]) courtStats[c] = { collected: 0, absent: 0 };
      courtStats[c].collected++;
    }
    for (const c of (item.tribunais_ausentes || [])) {
      if (!courtStats[c]) courtStats[c] = { collected: 0, absent: 0 };
      courtStats[c].absent++;
    }
  }

  const courtArray: CourtStat[] = Object.keys(courtStats).map(c => {
    const total = courtStats[c].collected + courtStats[c].absent;
    const rate = total > 0 ? courtStats[c].collected / total : 0;
    return { court: c, rate, total, collected: courtStats[c].collected, absent: courtStats[c].absent };
  });

  courtArray.sort((a, b) => b.rate - a.rate || b.total - a.total);
  const top5 = courtArray.slice(0, 5);
  const bottom5 = [...courtArray].sort((a, b) => a.rate - b.rate || b.total - a.total).slice(0, 5);

  return { top5, bottom5 };
}

export function processWeeklyPattern(
  data: Record<string, CompletedItem>
): { weeklyAverages: WeeklyAverage[]; lowestDay: WeeklyAverage | null } {
  const sortedDates = Object.keys(data).sort((a, b) => b.localeCompare(a));
  const weekdayStats: Record<number, { totalCount: number; days: number }> = {};
  for (let i = 0; i < 7; i++) weekdayStats[i] = { totalCount: 0, days: 0 };

  for (const dateStr of sortedDates) {
    const item = data[dateStr];
    const d = parseDateKey(dateStr);
    if (d) {
      const wDay = d.getUTCDay();
      weekdayStats[wDay].totalCount += (item.tribunal_count || 0);
      weekdayStats[wDay].days++;
    }
  }

  const weeklyAverages: WeeklyAverage[] = DAY_NAMES.map((name, i) => {
    const stats = weekdayStats[i];
    const avg = stats.days > 0 ? stats.totalCount / stats.days : 0;
    return {
      dayIdx: i,
      name,
      avg,
      avgPct: (avg / 91) * 100,
      daysCount: stats.days,
    };
  });

  let lowestDay: WeeklyAverage | null = null;
  let lowestAvg = 999;
  for (const w of weeklyAverages) {
    if (w.daysCount > 0 && w.avg < lowestAvg) {
      lowestAvg = w.avg;
      lowestDay = w;
    }
  }

  return { weeklyAverages, lowestDay };
}
