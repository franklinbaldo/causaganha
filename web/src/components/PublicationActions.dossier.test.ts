import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PublicationActions from './PublicationActions.svelte';

describe('PublicationActions — process handoff', () => {
  it('shows dossier and full-text as distinct destinations', () => {
    const component = render(PublicationActions, {
      props: {
        link: 'https://example.test/inteiro-teor',
        processHref: '/causaganha/processo?cnj=0000001-02.2024.8.22.0001',
        shareContext: 'main',
        onShare: vi.fn(),
      },
    });

    const dossier = component.getByText('Abrir dossiê');
    const fullText = component.getByText('Inteiro teor');

    expect(dossier.getAttribute('href')).toBe('/causaganha/processo?cnj=0000001-02.2024.8.22.0001');
    expect(fullText.getAttribute('href')).toBe('https://example.test/inteiro-teor');
  });

  it('does not invent a dossier action when the publication has no process number', () => {
    const component = render(PublicationActions, {
      props: {
        shareContext: 'compact',
        onShare: vi.fn(),
      },
    });

    expect(component.queryByText('Abrir dossiê')).toBeNull();
  });
});
