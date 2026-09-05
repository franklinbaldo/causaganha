import { render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import PublicationCard from './PublicationCard.svelte';
import type { DjenPublication } from '../lib/djen';

function pub(overrides: Partial<DjenPublication> = {}): DjenPublication {
  return {
    id: 1,
    numero_processo: '00000010220248220001',
    siglaTribunal: 'TJRO',
    tipoComunicacao: 'Intimação',
    link: 'https://archive.org/download/djen-tjro-2024/djen-2024-01-01-TJRO.zip',
    ...overrides,
  };
}

describe('PublicationCard — copy reference (#1135 /publicacoes slice)', () => {
  it('copies a plain-text reference built from the publication, with the origin URL before the CausaGanha permalink', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    window.history.replaceState(null, '', '/causaganha/publicacoes?siglaTribunal=TJRO');

    const component = render(PublicationCard, {
      props: { pub: pub(), seq: 1, dateStr: '2024-01-01' },
    });

    await component.getByText('Copiar referência').click();

    expect(writeText).toHaveBeenCalledTimes(1);
    const text = writeText.mock.calls[0][0] as string;
    expect(text).toContain('DJEN');
    expect(text).toContain('TJRO');
    expect(text).toContain('Intimação');
    expect(text).toContain('2024-01-01');
    expect(text).toContain('0000001-02.2024.8.22.0001');
    expect(text).toContain('https://archive.org/download/djen-tjro-2024/djen-2024-01-01-TJRO.zip');
    expect(text).toContain(window.location.origin);
    expect(text.indexOf('https://archive.org/download/djen-tjro-2024/djen-2024-01-01-TJRO.zip')).toBeLessThan(
      text.indexOf(window.location.origin),
    );
    await component.findByText('Referência copiada');
  });

  it('never fabricates a process number when the publication carries none', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });

    const component = render(PublicationCard, {
      props: { pub: pub({ numero_processo: undefined }), seq: 1, dateStr: '2024-01-01' },
    });

    await component.getByText('Copiar referência').click();
    const text = writeText.mock.calls[0][0] as string;
    expect(text).not.toMatch(/do processo|n\/a|desconhecid[ao]/i);
  });

  it('offers no "Copiar referência" action when the publication has no public origin URL', () => {
    const component = render(PublicationCard, {
      props: { pub: pub({ link: undefined }), seq: 1, dateStr: '2024-01-01' },
    });
    expect(component.queryByText('Copiar referência')).toBeNull();
  });
});
