import { describe, expect, it } from 'vitest';
import { attachHeroSearchHint } from './heroSearchHint';

function setup() {
  const input = document.createElement('input');
  const hint = document.createElement('p');
  hint.hidden = true;
  attachHeroSearchHint(input, hint);
  return { input, hint };
}

function type(input: HTMLInputElement, value: string): void {
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

describe('attachHeroSearchHint', () => {
  it('starts hidden with no mode when the input is empty', () => {
    const { hint } = setup();
    expect(hint.hidden).toBe(true);
    expect(hint.dataset.mode).toBeUndefined();
    expect(hint.textContent).toBe('');
  });

  it('reveals "Abrir dossiê do processo" for a valid CNJ, marked as mode=processo', () => {
    const { input, hint } = setup();
    type(input, '0000001-02.2024.8.22.0001');
    expect(hint.hidden).toBe(false);
    expect(hint.dataset.mode).toBe('processo');
    expect(hint.textContent).toBe('Abrir dossiê do processo');
  });

  it('reveals "Pesquisar publicações" for OAB/free text, marked as mode=publicacoes', () => {
    const { input, hint } = setup();
    type(input, 'OAB/SP 245.812');
    expect(hint.hidden).toBe(false);
    expect(hint.dataset.mode).toBe('publicacoes');
    expect(hint.textContent).toBe('Pesquisar publicações');
  });

  it('hides the hint again once the input is cleared', () => {
    const { input, hint } = setup();
    type(input, 'Banco Itaú');
    expect(hint.hidden).toBe(false);
    type(input, '');
    expect(hint.hidden).toBe(true);
    expect(hint.textContent).toBe('');
  });

  it('sets the hint synchronously on attach, matching the input value already present', () => {
    const input = document.createElement('input');
    input.value = '00000010220248220001';
    const hint = document.createElement('p');
    hint.hidden = true;
    attachHeroSearchHint(input, hint);
    expect(hint.hidden).toBe(false);
    expect(hint.dataset.mode).toBe('processo');
  });
});
