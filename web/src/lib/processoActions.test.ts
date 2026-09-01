import { describe, expect, it } from 'vitest';
import { absoluteUrl, buildProcessoPermalink, buildPublicacoesCnjUrl } from './processoActions';

const CNJ = '00000010220248220001';

describe('processoActions', () => {
  it('builds a reproducible processo permalink under the configured base', () => {
    expect(buildProcessoPermalink('/causaganha/', CNJ)).toBe(
      '/causaganha/processo?cnj=00000010220248220001',
    );
  });

  it('reuses the canonical DJEN numeroProcesso URL filter', () => {
    expect(buildPublicacoesCnjUrl('/causaganha', CNJ)).toBe(
      '/causaganha/publicacoes?numeroProcesso=00000010220248220001',
    );
  });

  it('turns an app-relative permalink into a shareable absolute URL', () => {
    expect(
      absoluteUrl('/causaganha/processo?cnj=00000010220248220001', 'https://example.test'),
    ).toBe('https://example.test/causaganha/processo?cnj=00000010220248220001');
  });
});
