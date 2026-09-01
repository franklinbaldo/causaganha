import { describe, expect, it } from 'vitest';
import { formatCnj } from './processoCnj';
import {
  parseSavedConsultations,
  removeSavedConsultation,
  renameSavedConsultation,
  saveProcessConsultation,
  saveSearchConsultation,
  searchConsultationId,
  serializeSavedConsultations,
} from './savedConsultations';

const CNJ = '0000001-02.2024.8.22.0001';
const DIGITS = '00000010220248220001';

describe('savedConsultations', () => {
  it('normalizes and stores a process consultation', () => {
    const items = saveProcessConsultation([], CNJ, 'Caso teste', '2026-08-21T12:00:00.000Z');

    expect(items).toEqual([
      {
        id: `processo:${DIGITS}`,
        type: 'processo',
        cnj: DIGITS,
        label: 'Caso teste',
        savedAt: '2026-08-21T12:00:00.000Z',
      },
    ]);
  });

  it('deduplicates the same CNJ and preserves the original savedAt', () => {
    const first = saveProcessConsultation([], CNJ, '', '2026-08-20T12:00:00.000Z');
    const second = saveProcessConsultation(first, DIGITS, 'Apelido', '2026-08-21T12:00:00.000Z');

    expect(second).toHaveLength(1);
    expect(second[0].label).toBe('Apelido');
    expect(second[0].savedAt).toBe('2026-08-20T12:00:00.000Z');
  });

  it('round-trips valid data and drops malformed entries', () => {
    const valid = saveProcessConsultation([], CNJ, 'Caso', '2026-08-21T12:00:00.000Z');
    const raw = JSON.stringify([
      ...valid,
      { id: 'bad', type: 'processo', cnj: '123', label: 'inválido', savedAt: 'x' },
      { type: 'other' },
    ]);

    expect(parseSavedConsultations(raw)).toEqual(valid);
    expect(parseSavedConsultations(serializeSavedConsultations(valid))).toEqual(valid);
    expect(parseSavedConsultations('{')).toEqual([]);
  });

  it('renames and removes without mutating unrelated items', () => {
    const items = saveProcessConsultation([], CNJ, 'Original', '2026-08-21T12:00:00.000Z');
    const renamed = renameSavedConsultation(items, items[0].id, 'Novo nome');

    expect(renamed[0].label).toBe('Novo nome');
    expect(removeSavedConsultation(renamed, items[0].id)).toEqual([]);
  });

  it('rejects invalid CNJs', () => {
    expect(() => saveProcessConsultation([], '123')).toThrow('CNJ inválido');
  });
});

describe('savedConsultations — DJEN search (busca)', () => {
  it('saves a search keyed by its canonical params', () => {
    const items = saveSearchConsultation(
      [],
      { siglaTribunal: 'TJRO', texto: 'contrato' },
      'Contratos TJRO',
      '2026-08-21T12:00:00.000Z',
    );

    expect(items).toEqual([
      {
        id: searchConsultationId({ siglaTribunal: 'TJRO', texto: 'contrato' }),
        type: 'busca',
        params: 'siglaTribunal=TJRO&texto=contrato',
        label: 'Contratos TJRO',
        savedAt: '2026-08-21T12:00:00.000Z',
      },
    ]);
  });

  it('treats page and key order as the same search identity', () => {
    const idA = searchConsultationId({ texto: 'contrato', siglaTribunal: 'TJRO', pagina: 1 });
    const idB = searchConsultationId({ pagina: 3, siglaTribunal: 'TJRO', texto: 'contrato' });

    expect(idA).toBe(idB);
  });

  it('deduplicates the same search and preserves the original savedAt', () => {
    const first = saveSearchConsultation(
      [],
      { siglaTribunal: 'TJRO', texto: 'contrato' },
      'Primeiro nome',
      '2026-08-20T12:00:00.000Z',
    );
    const second = saveSearchConsultation(
      first,
      { siglaTribunal: 'TJRO', texto: 'contrato', pagina: 2 },
      'Apelido novo',
      '2026-08-21T12:00:00.000Z',
    );

    expect(second).toHaveLength(1);
    expect(second[0].label).toBe('Apelido novo');
    expect(second[0].savedAt).toBe('2026-08-20T12:00:00.000Z');
  });

  it('keeps the previous label when saving again without an explicit one', () => {
    const first = saveSearchConsultation([], { siglaTribunal: 'TJRO' }, 'Meu apelido');
    const second = saveSearchConsultation(first, { siglaTribunal: 'TJRO' });

    expect(second[0].label).toBe('Meu apelido');
  });

  it('rejects a search with no criteria at all', () => {
    expect(() => saveSearchConsultation([], {})).toThrow('Busca vazia');
    expect(() => saveSearchConsultation([], { pagina: 2, itensPorPagina: 30 })).toThrow(
      'Busca vazia',
    );
  });

  it('migrates a legacy busca record missing `label` instead of dropping it', () => {
    const params = 'siglaTribunal=TJRO&texto=contrato';
    const legacyRaw = JSON.stringify([{ type: 'busca', params, savedAt: '2026-08-21T12:00:00.000Z' }]);

    expect(parseSavedConsultations(legacyRaw)).toEqual([
      {
        id: `busca:${params}`,
        type: 'busca',
        params,
        label: 'Busca DJEN',
        savedAt: '2026-08-21T12:00:00.000Z',
      },
    ]);
  });

  it('round-trips mixed processo + busca entries and drops malformed ones', () => {
    const withProcess = saveProcessConsultation([], CNJ, 'Caso', '2026-08-21T12:00:00.000Z');
    const withBoth = saveSearchConsultation(
      withProcess,
      { siglaTribunal: 'TJRO' },
      'Busca TJRO',
      '2026-08-22T12:00:00.000Z',
    );

    const raw = JSON.stringify([
      ...withBoth,
      { type: 'busca', params: '', label: 'vazio', savedAt: '2026-08-01T00:00:00.000Z' },
      { type: 'busca', label: 'sem params', savedAt: '2026-08-01T00:00:00.000Z' },
    ]);

    expect(parseSavedConsultations(raw)).toEqual(withBoth);
    expect(parseSavedConsultations(serializeSavedConsultations(withBoth))).toEqual(withBoth);
  });

  it('migrates a legacy processo record missing `label` instead of dropping it', () => {
    // Minimal fixture for a pre-label schema shape (label was introduced
    // after `type`/`cnj`/`savedAt`) — a record like this should recover a
    // derived label, not be silently discarded as malformed.
    const legacyRaw = JSON.stringify([{ type: 'processo', cnj: CNJ, savedAt: '2026-08-21T12:00:00.000Z' }]);

    expect(parseSavedConsultations(legacyRaw)).toEqual([
      {
        id: `processo:${DIGITS}`,
        type: 'processo',
        cnj: DIGITS,
        label: formatCnj(DIGITS),
        savedAt: '2026-08-21T12:00:00.000Z',
      },
    ]);
  });

  it('renames and removes a busca item alongside a processo item', () => {
    const withProcess = saveProcessConsultation([], CNJ, 'Caso', '2026-08-21T12:00:00.000Z');
    const items = saveSearchConsultation(withProcess, { siglaTribunal: 'TJRO' }, 'Busca TJRO');
    const searchId = items.find((item) => item.type === 'busca')!.id;

    const renamed = renameSavedConsultation(items, searchId, 'Novo nome da busca');
    expect(renamed.find((item) => item.id === searchId)?.label).toBe('Novo nome da busca');
    expect(renamed.find((item) => item.type === 'processo')?.label).toBe('Caso');

    const removed = removeSavedConsultation(renamed, searchId);
    expect(removed).toHaveLength(1);
    expect(removed[0].type).toBe('processo');
  });
});
