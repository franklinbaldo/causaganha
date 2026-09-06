import { beforeEach, describe, expect, it } from 'vitest';
import {
  CONSULTATION_SNAPSHOTS_STORAGE_KEY,
  getConsultationSnapshot,
  removeConsultationSnapshot,
  saveConsultationSnapshot,
} from './consultationSnapshotStore';
import type { ConsultationSnapshot } from './consultationSnapshot';

const SNAPSHOT: ConsultationSnapshot = {
  version: 1,
  capturedAt: '2026-09-01T12:00:00Z',
  encontrado: true,
  datasetGeradoEm: '2026-09-01T00:00:00Z',
  fontesPresentes: ['djen'],
  fontesIndisponiveis: [],
  djen: { nPublicacoes: 3, ultimaPub: '2026-01-10' },
  juris: null,
  stj: null,
  datajud: null,
};

beforeEach(() => {
  localStorage.clear();
});

describe('consultationSnapshotStore', () => {
  it('returns null for a consultation with no stored snapshot', () => {
    expect(getConsultationSnapshot('processo:00000010220248220001')).toBeNull();
  });

  it('round-trips a snapshot keyed by consultation id', () => {
    saveConsultationSnapshot('processo:00000010220248220001', SNAPSHOT);
    expect(getConsultationSnapshot('processo:00000010220248220001')).toEqual(SNAPSHOT);
  });

  it('keeps snapshots for different consultations independent', () => {
    saveConsultationSnapshot('processo:a', SNAPSHOT);
    saveConsultationSnapshot('processo:b', { ...SNAPSHOT, djen: { nPublicacoes: 9, ultimaPub: '2026-05-01' } });

    expect(getConsultationSnapshot('processo:a')).toEqual(SNAPSHOT);
    expect(getConsultationSnapshot('processo:b')?.djen).toEqual({ nPublicacoes: 9, ultimaPub: '2026-05-01' });
  });

  it('removes a snapshot without touching the others', () => {
    saveConsultationSnapshot('processo:a', SNAPSHOT);
    saveConsultationSnapshot('processo:b', SNAPSHOT);

    removeConsultationSnapshot('processo:a');

    expect(getConsultationSnapshot('processo:a')).toBeNull();
    expect(getConsultationSnapshot('processo:b')).toEqual(SNAPSHOT);
  });

  it('tolerates a corrupted or pre-existing incompatible value at the storage key', () => {
    localStorage.setItem(CONSULTATION_SNAPSHOTS_STORAGE_KEY, '{not json');
    expect(getConsultationSnapshot('processo:a')).toBeNull();
    expect(() => saveConsultationSnapshot('processo:a', SNAPSHOT)).not.toThrow();
    expect(getConsultationSnapshot('processo:a')).toEqual(SNAPSHOT);
  });
});
