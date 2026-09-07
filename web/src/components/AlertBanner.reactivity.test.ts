import { cleanup, screen } from '@testing-library/svelte/pure';
import { afterEach, describe, expect, it } from 'vitest';
import AlertBannerRaw from './AlertBanner.svelte';
import { render } from './__steps__/shared';

const AlertBanner = AlertBannerRaw as unknown as Parameters<typeof render>[0];

describe('AlertBanner — role reacts to prop updates', () => {
  afterEach(() => {
    cleanup();
  });

  it('switches role from note to alert when level changes on a live instance', async () => {
    const { rerender } = render(AlertBanner, {
      title: 'Título',
      message: 'Mensagem',
      level: 'info',
    });

    expect(screen.getByRole('note')).toBeTruthy();

    await rerender({ title: 'Título', message: 'Mensagem', level: 'error' });

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.queryByRole('note')).toBeNull();
  });

  it('switches role from alert to note when an explicit live prop is toggled off', async () => {
    const { rerender } = render(AlertBanner, {
      title: 'Título',
      message: 'Mensagem',
      level: 'error',
      live: true,
    });

    expect(screen.getByRole('alert')).toBeTruthy();

    await rerender({ title: 'Título', message: 'Mensagem', level: 'error', live: false });

    expect(screen.getByRole('note')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
