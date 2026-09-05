import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PublicationActions from './PublicationActions.svelte';

describe('PublicationActions — copy reference (#1135 /publicacoes slice)', () => {
  it('offers "Copiar referência" when a public origin URL (link) exists', () => {
    const withLink = render(PublicationActions, {
      props: {
        link: 'https://archive.org/download/djen-tjro-2024/djen-2024-01-01-TJRO.zip',
        shareContext: 'main',
        onShare: vi.fn(),
        onCopyReference: vi.fn(),
      },
    });
    expect(withLink.getByText('Copiar referência')).toBeTruthy();
  });

  it('does not offer "Copiar referência" when there is no public origin URL', () => {
    const withoutLink = render(PublicationActions, {
      props: {
        shareContext: 'compact',
        onShare: vi.fn(),
        onCopyReference: vi.fn(),
      },
    });
    expect(withoutLink.queryByText('Copiar referência')).toBeNull();
  });

  it('calls onCopyReference with the action context when clicked, and shows a text-based copied state', async () => {
    const onCopyReference = vi.fn();
    const component = render(PublicationActions, {
      props: {
        link: 'https://archive.org/download/djen-tjro-2024/djen-2024-01-01-TJRO.zip',
        shareContext: 'reader',
        onShare: vi.fn(),
        onCopyReference,
        activeReferenceCopied: null,
      },
    });

    const button = component.getByText('Copiar referência');
    await button.click();
    expect(onCopyReference).toHaveBeenCalledTimes(1);
    expect(onCopyReference.mock.calls[0][1]).toBe('reader');

    component.rerender({
      link: 'https://archive.org/download/djen-tjro-2024/djen-2024-01-01-TJRO.zip',
      shareContext: 'reader',
      onShare: vi.fn(),
      onCopyReference,
      activeReferenceCopied: 'reader',
    });
    expect(component.getByText('Referência copiada')).toBeTruthy();
  });
});
