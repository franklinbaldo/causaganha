import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { WorkflowStatusBadge } from './WorkflowStatusBadge';
import * as useWorkflowHook from '../lib/useWorkflowStatus';

// Mock the hook
vi.mock('../lib/useWorkflowStatus', () => ({
  useWorkflowStatus: vi.fn(),
}));

const mockUseWorkflowStatus = useWorkflowHook.useWorkflowStatus as Mock;

describe('WorkflowStatusBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders nothing when not running', () => {
    mockUseWorkflowStatus.mockReturnValue({
      isRunning: false,
      startedAt: null,
      elapsedMs: 0,
      error: null,
    });

    const { container } = render(<WorkflowStatusBadge />);
    expect(container.firstChild).toBeNull();
  });

  it('renders badge with correct elapsed time when running', () => {
    mockUseWorkflowStatus.mockReturnValue({
      isRunning: true,
      startedAt: Date.now() - 65000, // 65 seconds ago
      elapsedMs: 65000,
      error: null,
    });

    render(<WorkflowStatusBadge />);

    expect(screen.getByText('Coletando agora...')).toBeTruthy();

    // 65000ms = 65s = 1:05
    expect(screen.getByText('01:05')).toBeTruthy();
  });

  it('formats time correctly for less than a minute', () => {
    mockUseWorkflowStatus.mockReturnValue({
      isRunning: true,
      startedAt: Date.now() - 45000, // 45 seconds ago
      elapsedMs: 45000,
      error: null,
    });

    render(<WorkflowStatusBadge />);
    expect(screen.getByText('00:45')).toBeTruthy();
  });

  it('formats time correctly for more than an hour', () => {
    mockUseWorkflowStatus.mockReturnValue({
      isRunning: true,
      startedAt: Date.now() - 3665000, // 1 hour, 1 minute, 5 seconds
      elapsedMs: 3665000,
      error: null,
    });

    render(<WorkflowStatusBadge />);
    // 3665000ms = 3665s = 61m 5s
    expect(screen.getByText('61:05')).toBeTruthy();
  });
});
