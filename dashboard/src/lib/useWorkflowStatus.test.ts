import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useWorkflowStatus } from './useWorkflowStatus';

describe('useWorkflowStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('initializes with default state', () => {
    global.fetch = vi.fn(() => new Promise(() => {})); // Never resolves

    const { result } = renderHook(() => useWorkflowStatus(60000));

    expect(result.current).toEqual({
      isRunning: false,
      startedAt: null,
      elapsedMs: 0,
      error: null,
    });
  });

  it('fetches workflow status and handles active run', async () => {
    const startedAt = new Date('2026-03-26T12:00:00Z');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        total_count: 1,
        workflow_runs: [
          {
            run_started_at: startedAt.toISOString(),
          }
        ]
      })
    });

    vi.setSystemTime(new Date('2026-03-26T12:05:00Z')); // 5 minutes later

    const { result } = renderHook(() => useWorkflowStatus(60000));

    // Wait for the async fetch to complete
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.github.com/repos/franklinbaldo/causaganha/actions/workflows/collect-zips.yml/runs?status=in_progress'
    );

    expect(result.current.isRunning).toBe(true);
    expect(result.current.startedAt).toBe(startedAt.getTime());
    expect(result.current.elapsedMs).toBe(5 * 60 * 1000); // 5 mins in ms
  });

  it('handles no active runs gracefully', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        total_count: 0,
        workflow_runs: []
      })
    });

    const { result } = renderHook(() => useWorkflowStatus(60000));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.startedAt).toBeNull();
  });

  it('handles fetch errors without crashing', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network failure'));

    const { result } = renderHook(() => useWorkflowStatus(60000));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.error).toBe('Network failure');
  });

  it('updates elapsed time every second while running', async () => {
    const startedAt = new Date('2026-03-26T12:00:00Z');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        total_count: 1,
        workflow_runs: [
          {
            run_started_at: startedAt.toISOString(),
          }
        ]
      })
    });

    vi.setSystemTime(new Date('2026-03-26T12:05:00Z').getTime());

    const { result } = renderHook(() => useWorkflowStatus(60000));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    // Capture initial value
    const initialElapsedMs = result.current.elapsedMs;

    // We do NOT setSystemTime here, just let timers naturally advance the time.
    // The elapsedMs logic in the hook uses Date.now(), which vi.advanceTimersByTimeAsync also controls
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    // Should be exactly 1000ms more (or 999 since we already advanced 1)
    expect(result.current.elapsedMs).toBeGreaterThan(initialElapsedMs);
    expect(result.current.elapsedMs - initialElapsedMs).toBe(1001); // 1 from initial fetch + 1000 from loop
  });
});
