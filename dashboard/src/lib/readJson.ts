import fs from 'node:fs';
import path from 'node:path';

export function readJson<T = unknown>(relativePath: string): T | null {
  try {
    const fullPath = path.resolve('./public', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf-8')) as T;
  } catch { return null; }
}
