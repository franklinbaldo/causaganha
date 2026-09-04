import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Security floors from upstream advisories reapplied after PR #868
// (fast-uri ReDoS, DOMPurify sanitizer hardening, PostCSS parsing fix).
const MINIMUM_VERSIONS: Record<string, string> = {
  dompurify: '3.4.13',
  'fast-uri': '3.1.5',
  postcss: '8.5.26',
};

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

function parseVersion(version: string): [number, number, number] {
  const match = /^(\d+)\.(\d+)\.(\d+)/.exec(version);
  if (!match) {
    throw new Error(`Cannot parse version: ${version}`);
  }
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function isAtLeast(version: string, minimum: string): boolean {
  const actual = parseVersion(version);
  const floor = parseVersion(minimum);
  for (let i = 0; i < 3; i += 1) {
    if (actual[i] > floor[i]) return true;
    if (actual[i] < floor[i]) return false;
  }
  return true;
}

describe('web dependency security floor', () => {
  const packageJson = JSON.parse(readFileSync(resolve(webRoot, 'package.json'), 'utf-8'));
  const packageLock = JSON.parse(readFileSync(resolve(webRoot, 'package-lock.json'), 'utf-8'));
  const pnpmLock = readFileSync(resolve(webRoot, 'pnpm-lock.yaml'), 'utf-8');

  it('declares dompurify >= 3.4.13 in package.json', () => {
    const range: string = packageJson.dependencies.dompurify;
    const version = range.replace(/^[\^~]/, '');
    expect(isAtLeast(version, MINIMUM_VERSIONS.dompurify)).toBe(true);
  });

  for (const [pkg, minVersion] of Object.entries(MINIMUM_VERSIONS)) {
    it(`package-lock.json locks ${pkg} at >= ${minVersion}`, () => {
      const entry = packageLock.packages?.[`node_modules/${pkg}`];
      expect(entry, `node_modules/${pkg} missing from package-lock.json`).toBeDefined();
      expect(isAtLeast(entry.version, minVersion)).toBe(true);
    });

    it(`pnpm-lock.yaml locks ${pkg} at >= ${minVersion}`, () => {
      const match = new RegExp(`^ {2}${pkg}@(\\d+\\.\\d+\\.\\d+):`, 'm').exec(pnpmLock);
      expect(match, `${pkg} entry missing from pnpm-lock.yaml`).not.toBeNull();
      expect(isAtLeast(match![1], minVersion)).toBe(true);
    });
  }
});
