import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import McpConfigCard from './McpConfigCard.svelte';

const CONFIG = `{
  "mcpServers": {
    "causaganha": {
      "command": "uv"
    }
  }
}`;

function setClipboard(writeText: ((text: string) => Promise<void>) | undefined) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: writeText ? { writeText } : undefined,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('McpConfigCard — copy action', () => {
  beforeEach(() => {
    setClipboard(vi.fn().mockResolvedValue(undefined));
  });

  it('shows the same config text it will copy, so there is no drift between shown and copied', () => {
    const component = render(McpConfigCard, { props: { config: CONFIG, label: 'stdio' } });

    expect(component.container.textContent).toContain(CONFIG);
  });

  it('copies the exact displayed JSON byte-for-byte when activated', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    const component = render(McpConfigCard, { props: { config: CONFIG, label: 'stdio' } });

    await fireEvent.click(component.getByText('Copiar configuração'));

    expect(writeText).toHaveBeenCalledWith(CONFIG);
  });

  it('announces success accessibly after a successful copy', async () => {
    const component = render(McpConfigCard, { props: { config: CONFIG, label: 'stdio' } });

    await fireEvent.click(component.getByText('Copiar configuração'));

    const status = await waitFor(() => component.getByRole('status'));
    expect(status.textContent).toMatch(/copiad/i);
  });

  it('announces failure accessibly instead of a silent or false success when writeText rejects', async () => {
    setClipboard(vi.fn().mockRejectedValue(new Error('denied')));
    const component = render(McpConfigCard, { props: { config: CONFIG, label: 'stdio' } });

    await fireEvent.click(component.getByText('Copiar configuração'));

    const status = await waitFor(() => component.getByRole('status'));
    expect(status.textContent).not.toMatch(/copiad/i);
    expect(status.textContent).toMatch(/n[ãa]o foi poss[íi]vel|falh/i);
  });

  it('does not throw and gives failure feedback, not false success, when navigator.clipboard is unavailable', async () => {
    setClipboard(undefined);
    const component = render(McpConfigCard, { props: { config: CONFIG, label: 'stdio' } });

    await fireEvent.click(component.getByText('Copiar configuração'));

    const status = await waitFor(() => component.getByRole('status'));
    expect(status.textContent).not.toMatch(/copiad/i);
    expect(status.textContent).toMatch(/n[ãa]o foi poss[íi]vel|falh|indispon[íi]vel/i);
  });

  it('is a real button reachable and activatable by keyboard, not a pointer-only handler', () => {
    const component = render(McpConfigCard, { props: { config: CONFIG, label: 'stdio' } });

    const button = component.getByText('Copiar configuração').closest('button');
    expect(button).not.toBeNull();
    expect(button?.getAttribute('type')).toBe('button');
  });
});
