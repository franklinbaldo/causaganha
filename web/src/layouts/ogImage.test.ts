import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = resolve(__dirname, '../../public');

// Minimal PNG IHDR reader: signature (8 bytes) + length (4) + "IHDR" (4),
// then width/height as big-endian uint32 — no image library needed.
function readPngSize(path: string): { width: number; height: number } {
  const buffer = readFileSync(path);
  const isPng = buffer.readUInt32BE(0) === 0x89504e47 && buffer.readUInt32BE(4) === 0x0d0a1a0a;
  if (!isPng) throw new Error(`${path} is not a valid PNG file`);
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

describe('Open Graph image fallback', () => {
  it('ships a 1200x630 PNG (SVG og:image is not rendered by social crawlers)', () => {
    const size = readPngSize(resolve(PUBLIC_DIR, 'og-image.png'));
    expect(size).toEqual({ width: 1200, height: 630 });
  });

  it('points the default og:image/twitter:image fallback at the PNG, not the SVG', () => {
    const layoutSource = readFileSync(resolve(__dirname, 'Layout.astro'), 'utf-8');
    expect(layoutSource).toMatch(/og-image\.png/);
    expect(layoutSource).not.toMatch(/og-image\.svg/);
  });
});
