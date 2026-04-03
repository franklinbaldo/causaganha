export interface VelocityResult {
  weeklyData: { weekOffset: number; collected: number }[];
  historicalAvgVelocity: number;
  currentVelocity: number;
  trend: number;
  baselineCoverage: number;
  currentCoverage: number;
  regressionDrop: number;
  hasEnoughHistory: boolean;
}

export function calculateVelocityAndRegression(
  coverageSet: Set<string>,
  targetRangeEndStr: string,
  tribunalStartDateStr: string | undefined
): VelocityResult | null {
  if (!tribunalStartDateStr) return null;

  const targetRangeEnd = new Date(targetRangeEndStr + "T00:00:00Z");
  const tribunalStartDate = new Date(tribunalStartDateStr + "T00:00:00Z");

  if (targetRangeEnd < tribunalStartDate) return null;

  const MS_PER_DAY = 1000 * 60 * 60 * 24;

  let totalHistoricalDays = 0;
  let totalHistoricalCollected = 0;

  let current30Days = 0;
  let current30Collected = 0;
  let baseline60Days = 0;
  let baseline60Collected = 0;

  const current = new Date(tribunalStartDate);
  while (current <= targetRangeEnd) {
    totalHistoricalDays++;
    const dStr = current.toISOString().split('T')[0];
    const isCollected = coverageSet.has(dStr);

    if (isCollected) {
      totalHistoricalCollected++;
    }

    const diffDays = Math.floor((targetRangeEnd.getTime() - current.getTime()) / MS_PER_DAY);
    if (diffDays < 30) {
      current30Days++;
      if (isCollected) current30Collected++;
    } else if (diffDays < 90) {
      baseline60Days++;
      if (isCollected) baseline60Collected++;
    }
    current.setUTCDate(current.getUTCDate() + 1);
  }

  const weeklyData: { weekOffset: number; collected: number }[] = [];
  let recent4WeeksCollected = 0;

  for (let w = 11; w >= 0; w--) {
    let weekCollected = 0;

    const weekEnd = new Date(targetRangeEnd.getTime() - w * 7 * MS_PER_DAY);
    const weekStart = new Date(weekEnd.getTime() - 6 * MS_PER_DAY);

    const day = new Date(weekStart);
    while (day <= weekEnd) {
      if (day >= tribunalStartDate) {
        const dStr = day.toISOString().split('T')[0];
        if (coverageSet.has(dStr)) weekCollected++;
      }
      day.setUTCDate(day.getUTCDate() + 1);
    }

    weeklyData.push({
      weekOffset: w,
      collected: weekCollected,
    });

    if (w < 4) {
      recent4WeeksCollected += weekCollected;
    }
  }

  const historicalAvgVelocity = (totalHistoricalCollected / totalHistoricalDays) * 7;
  const currentVelocity = recent4WeeksCollected / 4;

  const baselineCoverage = baseline60Days > 0 ? baseline60Collected / baseline60Days : 0;
  let currentCoverage = 0;
  if (current30Days > 0) currentCoverage = current30Collected / current30Days;

  let trend = 0;
  if (historicalAvgVelocity > 0) {
    trend = ((currentVelocity - historicalAvgVelocity) / historicalAvgVelocity) * 100;
  } else if (currentVelocity > 0) {
    trend = 100;
  }

  let regressionDrop = 0;
  if (baselineCoverage > 0) {
    regressionDrop = ((baselineCoverage - currentCoverage) / baselineCoverage) * 100;
  }

  return {
    weeklyData,
    historicalAvgVelocity,
    currentVelocity,
    trend,
    baselineCoverage: baselineCoverage * 100,
    currentCoverage: currentCoverage * 100,
    regressionDrop,
    hasEnoughHistory: totalHistoricalDays >= 10
  };
}
