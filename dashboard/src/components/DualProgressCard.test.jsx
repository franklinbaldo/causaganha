import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { DualProgressCard } from './DualProgressCard';

describe('DualProgressCard', () => {
  beforeEach(() => {
    global.fetch = vi.fn();
  });

  it('shows skeleton loader while loading', () => {
    global.fetch.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<DualProgressCard apiUrl="/test.json" />);
    
    // Skeleton should be visible (check for multiple skeleton elements)
    const skeletons = screen.getAllByRole('generic');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows error state with retry button when fetch fails', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'));
    
    render(<DualProgressCard apiUrl="/test.json" />);
    
    await waitFor(() => {
      expect(screen.getByText('FETCH FAILED')).toBeInTheDocument();
      expect(screen.getByText(/RETRY/)).toBeInTheDocument();
    });
  });

  it('renders progress data correctly', async () => {
    const mockData = {
      backfill_progress: {
        unique_days: 500,
        target_range: { total_days: 764, start: '2024-01-01', end: '2026-02-03' },
        progress_pct: 65.4,
        total_items: 50000,
        oldest_date: '2024-01-01',
        newest_date: '2025-05-15',
        last_updated: '2026-02-05T12:00:00Z',
      },
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    render(<DualProgressCard apiUrl="/test.json" />);

    await waitFor(() => {
      expect(screen.getByText('Pipeline Progress')).toBeInTheDocument();
      expect(screen.getByText('Collection')).toBeInTheDocument();
      expect(screen.getByText('Consolidation')).toBeInTheDocument();
      expect(screen.getByText('50,000')).toBeInTheDocument(); // Total items formatted
    });
  });

  it('retries fetch when retry button is clicked', async () => {
    global.fetch.mockRejectedValueOnce(new Error('Network error'));
    
    render(<DualProgressCard apiUrl="/test.json" />);
    
    await waitFor(() => {
      expect(screen.getByText('FETCH FAILED')).toBeInTheDocument();
    });

    const mockData = {
      backfill_progress: {
        unique_days: 100,
        target_range: { total_days: 764 },
        progress_pct: 13.1,
        total_items: 10000,
      },
    };

    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const retryButton = screen.getByText(/RETRY/);
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Pipeline Progress')).toBeInTheDocument();
    });
  });

  it('shows refresh icon and allows manual refresh', async () => {
    const mockData = {
      backfill_progress: {
        unique_days: 100,
        target_range: { total_days: 764 },
        progress_pct: 13.1,
        total_items: 10000,
        last_updated: '2026-02-05T12:00:00Z',
      },
    };

    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => mockData,
    });

    render(<DualProgressCard apiUrl="/test.json" />);

    await waitFor(() => {
      expect(screen.getByText('Pipeline Progress')).toBeInTheDocument();
    });

    const refreshButton = screen.getByTitle('Refresh data');
    expect(refreshButton).toBeInTheDocument();
    
    fireEvent.click(refreshButton);
    
    // Should trigger another fetch
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
