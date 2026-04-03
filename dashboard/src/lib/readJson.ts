import fs from 'node:fs';
import path from 'node:path';

export function readJson(relativePath: string) {
  try {
    const fullPath = path.resolve('./public', relativePath);
    return JSON.parse(fs.readFileSync(fullPath, 'utf-8'));
  } catch { return null; }
}
