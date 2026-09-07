import { cleanup } from '@testing-library/svelte/pure';
import { afterEach, describe, expect, it } from 'vitest';
import YearSummaryCardsRaw from './YearSummaryCards.svelte';
import { render } from './__steps__/shared';

const YearSummaryCards = YearSummaryCardsRaw as unknown as Parameters<typeof render>[0];

describe('YearSummaryCards — stat values react to prop updates', () => {
  afterEach(() => {
    cleanup();
  });

  it('updates displayed counts when complete/partial/low/missing props change on the same instance', async () => {
    const { container, rerender } = render(YearSummaryCards, {
      complete: 1,
      partial: 2,
      low: 3,
      missing: 4,
    });

    const readValues = () =>
      Array.from(container.querySelectorAll('.stat-value')).map((el) => el.textContent);

    expect(readValues()).toEqual(['1', '2', '3', '4']);

    // AnnualCoverageMonitor.svelte reuses the same <YearSummaryCards> instance
    // across year switches and query refetches (no {#key}), so props change
    // on a live instance rather than remounting it.
    await rerender({ complete: 10, partial: 20, low: 30, missing: 40 });

    expect(readValues()).toEqual(['10', '20', '30', '40']);
  });
});
