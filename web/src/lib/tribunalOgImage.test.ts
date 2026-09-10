import { describe, expect, it } from 'vitest';
import { tribunalOgImagePath } from './tribunalOgImage';

describe('tribunalOgImagePath', () => {
  it('returns the SVG path when the build is PROD and the tribunal has archived ZIPs', () => {
    expect(tribunalOgImagePath('TJRO', 42, true)).toBe('og/tjro.svg');
  });

  it('returns null for a tribunal with zero archived ZIPs, even in PROD', () => {
    expect(tribunalOgImagePath('CJF', 0, true)).toBeNull();
  });

  it('returns null outside a PROD build, even with archived ZIPs, since the SVG is only written in PROD', () => {
    expect(tribunalOgImagePath('TJRO', 42, false)).toBeNull();
  });
});
