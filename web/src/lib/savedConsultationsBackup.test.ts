import { describe, expect, it } from 'vitest';
import {
  SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION,
  mergeSavedConsultations,
  parseBackup,
  serializeBackup,
} from './savedConsultationsBackup';
import { saveProcessConsultation, saveSearchConsultation } from './savedConsultations';

const CNJ_A = '0000001-02.2024.8.22.0001';
const CNJ_B = '0000002-03.2024.8.22.0001';

describe('savedConsultationsBackup — export', () => {
  it('wraps the current items with an explicit schema version and export timestamp', () => {
    const items = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    const raw = serializeBackup(items, '2026-09-06T21:00:00.000Z');

    expect(JSON.parse(raw)).toEqual({
      schema_version: SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION,
      exported_at: '2026-09-06T21:00:00.000Z',
      items,
    });
  });
});

describe('savedConsultationsBackup — round-trip', () => {
  it('imports into empty storage and recreates equivalent items', () => {
    const withProcess = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    const items = saveSearchConsultation(
      withProcess,
      { siglaTribunal: 'TJRO', texto: 'contrato' },
      'Busca TJRO',
      '2026-08-22T12:00:00.000Z',
    );
    const raw = serializeBackup(items, '2026-09-06T21:00:00.000Z');

    const result = parseBackup(raw);

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.items).toEqual(items);
  });

  it('drops malformed entries inside an otherwise valid backup instead of failing the whole import', () => {
    const raw = JSON.stringify({
      schema_version: SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION,
      exported_at: '2026-09-06T21:00:00.000Z',
      items: [
        { id: 'processo:x', type: 'processo', cnj: '123', label: 'inválido', savedAt: 'x' },
        { type: 'other' },
      ],
    });

    const result = parseBackup(raw);

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.items).toEqual([]);
  });
});

describe('savedConsultationsBackup — atomic failure', () => {
  it('rejects invalid JSON without throwing', () => {
    const result = parseBackup('{ not json');
    expect(result).toEqual({ ok: false, error: expect.any(String) });
  });

  it('rejects a payload with no items array', () => {
    const result = parseBackup(JSON.stringify({ schema_version: 1 }));
    expect(result).toEqual({ ok: false, error: expect.any(String) });
  });

  it('rejects an unknown/future schema_version rather than guessing its shape', () => {
    const raw = JSON.stringify({ schema_version: 999, exported_at: 'x', items: [] });
    const result = parseBackup(raw);
    expect(result).toEqual({ ok: false, error: expect.any(String) });
  });

  it('rejects a bare array (not the versioned backup envelope) — this is not the live-storage format', () => {
    const items = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    const result = parseBackup(JSON.stringify(items));
    expect(result).toEqual({ ok: false, error: expect.any(String) });
  });
});

describe('savedConsultationsBackup — merge into existing storage', () => {
  it('adds new items and keeps the existing label on an id collision (predictable, existing wins)', () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Nome local', '2026-08-20T12:00:00.000Z');
    const imported = saveProcessConsultation([], CNJ_A, 'Nome do backup', '2026-08-25T12:00:00.000Z');
    const importedWithNew = saveProcessConsultation(
      imported,
      CNJ_B,
      'Caso novo',
      '2026-08-26T12:00:00.000Z',
    );

    const merged = mergeSavedConsultations(existing, importedWithNew);

    expect(merged).toHaveLength(2);
    const a = merged.find((item) => item.id === existing[0].id);
    expect(a?.label).toBe('Nome local');
    expect(a?.savedAt).toBe('2026-08-20T12:00:00.000Z');
    const b = merged.find((item) => item.id !== a?.id);
    expect(b?.label).toBe('Caso novo');
  });

  it('is idempotent: importing the same backup twice does not duplicate items', () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    const merged = mergeSavedConsultations(existing, existing);
    expect(merged).toEqual(existing);
  });

  it('sorts the merged result newest-first, matching every other mutator', () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-20T12:00:00.000Z');
    const imported = saveProcessConsultation([], CNJ_B, 'Caso B', '2026-08-25T12:00:00.000Z');

    const merged = mergeSavedConsultations(existing, imported);

    expect(merged[0].savedAt).toBe('2026-08-25T12:00:00.000Z');
    expect(merged[1].savedAt).toBe('2026-08-20T12:00:00.000Z');
  });

  it('merges an empty import as a no-op', () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    expect(mergeSavedConsultations(existing, [])).toEqual(existing);
  });
});
