import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const indexSource = readFileSync(resolve(__dirname, 'index.astro'), 'utf-8');

describe('Home CTA for the agents surface (#1219)', () => {
  it('offers a visible CTA to /agentes on the home page', () => {
    expect(indexSource).toMatch(/href=\{BASE \+ 'agentes'\}/);
    expect(indexSource).toMatch(/Usar com um agente/i);
  });

  it('makes clear an agent queries the same archive, not a separate API', () => {
    expect(indexSource).toMatch(/mesmo acervo/i);
  });

  it('keeps Processo and Publicações as the primary human entries', () => {
    expect(indexSource).toMatch(/href=\{BASE \+ 'processo'\}/);
    expect(indexSource).toMatch(/href=\{BASE \+ 'publicacoes'\}/);
    expect(indexSource).toMatch(/Consultar processo/);
    expect(indexSource).toMatch(/Pesquisar publicações/);
  });

  it('does not announce a remote MCP endpoint URL ahead of #950 operational proof', () => {
    expect(indexSource).not.toMatch(/https?:\/\//);
  });
});
