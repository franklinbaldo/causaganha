import { describe, it, expect } from 'vitest';
import {
  smartParseInput,
  queryToSearchParams,
  searchParamsToQuery,
  hasAnyQueryValue,
} from '../../lib/searchQueryString';
import type { DjenComunicacaoQuery } from '../../lib/djen';

describe('smartParseInput', () => {
  it('detects canonical CNJ process numbers and strips the mask', () => {
    const result = smartParseInput('1234567-89.2024.8.26.0100');
    expect(result.kind).toBe('processo');
    expect(result.patch.numeroProcesso).toBe('12345678920248260100');
    expect(result.label).toContain('CNJ');
  });

  it('detects bare 20-digit CNJ numbers', () => {
    const result = smartParseInput('12345678920248260100');
    expect(result.kind).toBe('processo');
    expect(result.patch.numeroProcesso).toBe('12345678920248260100');
  });

  it('detects "OAB/SP 123456" format', () => {
    const result = smartParseInput('OAB/SP 123456');
    expect(result.kind).toBe('oab');
    expect(result.patch.ufOab).toBe('SP');
    expect(result.patch.numeroOab).toBe('123456');
  });

  it('detects "OAB SP 123456" format', () => {
    const result = smartParseInput('OAB SP 123456');
    expect(result.kind).toBe('oab');
    expect(result.patch.ufOab).toBe('SP');
    expect(result.patch.numeroOab).toBe('123456');
  });

  it('detects bare "SP 123456" format', () => {
    const result = smartParseInput('SP 123456');
    expect(result.kind).toBe('oab');
    expect(result.patch.ufOab).toBe('SP');
    expect(result.patch.numeroOab).toBe('123456');
  });

  it('falls back to texto for free-text input', () => {
    const result = smartParseInput('contrato de aluguel');
    expect(result.kind).toBe('texto');
    expect(result.patch.texto).toBe('contrato de aluguel');
  });

  it('returns empty patch for empty input', () => {
    const result = smartParseInput('');
    expect(result.kind).toBe('texto');
    expect(result.patch).toEqual({});
    expect(result.label).toBe('');
  });
});

describe('queryToSearchParams / searchParamsToQuery', () => {
  it('skips undefined and empty values', () => {
    const q: DjenComunicacaoQuery = {
      siglaTribunal: 'TJSP',
      texto: '',
      numeroProcesso: undefined,
      pagina: 2,
    };
    const params = queryToSearchParams(q);
    expect(params.get('siglaTribunal')).toBe('TJSP');
    expect(params.get('texto')).toBeNull();
    expect(params.get('numeroProcesso')).toBeNull();
    expect(params.get('pagina')).toBe('2');
  });

  it('round-trips string values and coerces numeric keys', () => {
    const input: DjenComunicacaoQuery = {
      siglaTribunal: 'TJSP',
      texto: 'contrato',
      numeroOab: '123456',
      ufOab: 'SP',
      pagina: 2,
      itensPorPagina: 30,
    };
    const roundTripped = searchParamsToQuery(queryToSearchParams(input));
    expect(roundTripped.siglaTribunal).toBe('TJSP');
    expect(roundTripped.texto).toBe('contrato');
    expect(roundTripped.numeroOab).toBe('123456');
    expect(roundTripped.ufOab).toBe('SP');
    expect(roundTripped.pagina).toBe(2);
    expect(roundTripped.itensPorPagina).toBe(30);
  });
});

describe('hasAnyQueryValue', () => {
  it('returns false when the query is empty', () => {
    expect(hasAnyQueryValue({})).toBe(false);
  });

  it('returns true when at least one value is set', () => {
    expect(hasAnyQueryValue({ siglaTribunal: 'TJSP' })).toBe(true);
    expect(hasAnyQueryValue({ texto: 'contrato' })).toBe(true);
  });

  it('ignores empty strings', () => {
    expect(hasAnyQueryValue({ texto: '', siglaTribunal: '' })).toBe(false);
  });
});
