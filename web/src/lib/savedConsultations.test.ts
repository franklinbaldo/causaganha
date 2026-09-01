import { describe, expect, it } from 'vitest';
import {
  parseSavedConsultations,
  removeSavedConsultation,
  renameSavedConsultation,
  saveProcessConsultation,
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
