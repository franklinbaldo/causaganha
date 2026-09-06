import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SavedConsultations from './SavedConsultations.svelte';
import { getDuckDB } from '../lib/duckdbSingleton';
import * as processoCnj from '../lib/processoCnj';
import {
  SAVED_CONSULTATIONS_STORAGE_KEY,
  saveProcessConsultation,
  serializeSavedConsultations,
} from '../lib/savedConsultations';
import {
  CONSULTATION_SNAPSHOTS_STORAGE_KEY,
  getConsultationSnapshot,
} from '../lib/consultationSnapshotStore';
import { formatFonteIndisponivelAviso } from '../lib/processoCnj';

vi.mock('../lib/duckdbSingleton', () => ({ getDuckDB: vi.fn() }));
vi.mock('../lib/processoCnj', async () => {
  const actual = await vi.importActual<typeof import('../lib/processoCnj')>('../lib/processoCnj');
  return { ...actual, buscarProcesso: vi.fn() };
});

const CNJ = '0000001-02.2024.8.22.0001';
const DIGITS = '00000010220248220001';
const ID = `processo:${DIGITS}`;

const AUSENTE_JURIS = {
  present: false,
  nDocumentos: null,
  tipos: [],
  dataJulgamento: null,
  orgao: null,
  relator: null,
  classe: null,
  url: null,
};
const AUSENTE_STJ = {
  present: false,
  id: null,
  classe: null,
  relator: null,
  tema: null,
  tese: null,
  ementa: null,
  dataDecisao: null,
  dataPublicacao: null,
};
const AUSENTE_DATAJUD = {
  present: false,
  classeOficial: null,
  assuntos: null,
  orgaoJulgador: null,
  grau: null,
  dataAjuizamento: null,
  ultimaAtualizacao: null,
};

function resultadoWith(nPublicacoes: number, avisos: string[] = []) {
  return {
    encontrado: true,
    nrProcesso: DIGITS,
    nrProcessoMascara: CNJ,
    fontes: ['djen'],
    djen: { present: true, primeiraPub: '2026-01-01', ultimaPub: '2026-01-10', nPublicacoes, tribunais: ['TJRO'] },
    juris: AUSENTE_JURIS,
    stj: AUSENTE_STJ,
    datajud: AUSENTE_DATAJUD,
    jurisUrls: [],
    stjUrls: [],
    cobertura: [],
    datasetGeradoEm: '2026-09-01T00:00:00Z',
    avisos,
  };
}

function saveItem() {
  const items = saveProcessConsultation([], CNJ, 'Caso teste', '2026-08-21T12:00:00.000Z');
  localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(getDuckDB).mockResolvedValue({ conn: {} } as never);
});

describe('SavedConsultations — mudou desde a última consulta (#1133)', () => {
  it('shows no verdict yet on the very first capture of a saved processo', async () => {
    saveItem();
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(resultadoWith(3) as never);

    const component = render(SavedConsultations);

    await waitFor(() => expect(getConsultationSnapshot(ID)).not.toBeNull());
    expect(component.queryByText(/Mudou desde/)).toBeNull();
    expect(component.queryByText(/Sem mudanças desde/)).toBeNull();
  });

  it('flags a real observable change on the next visit', async () => {
    localStorage.setItem(
      CONSULTATION_SNAPSHOTS_STORAGE_KEY,
      JSON.stringify({
        [ID]: {
          version: 1,
          capturedAt: '2026-08-01T00:00:00Z',
          encontrado: true,
          datasetGeradoEm: '2026-08-01T00:00:00Z',
          fontesPresentes: ['djen'],
          fontesIndisponiveis: [],
          djen: { nPublicacoes: 3, ultimaPub: '2026-01-10' },
          juris: null,
          stj: null,
          datajud: null,
        },
      }),
    );
    saveItem();
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(resultadoWith(5) as never);

    const component = render(SavedConsultations);

    await waitFor(() => expect(component.getByText(/Mudou desde a última consulta/)).toBeTruthy());
  });

  it('reports no change when the observable fields are identical to the last capture', async () => {
    localStorage.setItem(
      CONSULTATION_SNAPSHOTS_STORAGE_KEY,
      JSON.stringify({
        [ID]: {
          version: 1,
          capturedAt: '2026-08-01T00:00:00Z',
          encontrado: true,
          datasetGeradoEm: '2026-08-01T00:00:00Z',
          fontesPresentes: ['djen'],
          fontesIndisponiveis: [],
          djen: { nPublicacoes: 3, ultimaPub: '2026-01-10' },
          juris: null,
          stj: null,
          datajud: null,
        },
      }),
    );
    saveItem();
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(resultadoWith(3) as never);

    const component = render(SavedConsultations);

    await waitFor(() => expect(component.getByText(/Sem mudanças desde a última consulta/)).toBeTruthy());
  });

  it('never reports a change when the only difference is a source becoming temporarily unavailable', async () => {
    localStorage.setItem(
      CONSULTATION_SNAPSHOTS_STORAGE_KEY,
      JSON.stringify({
        [ID]: {
          version: 1,
          capturedAt: '2026-08-01T00:00:00Z',
          encontrado: true,
          datasetGeradoEm: '2026-08-01T00:00:00Z',
          fontesPresentes: ['djen'],
          fontesIndisponiveis: [],
          djen: { nPublicacoes: 3, ultimaPub: '2026-01-10' },
          juris: null,
          stj: null,
          datajud: null,
        },
      }),
    );
    saveItem();
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(
      resultadoWith(3, [formatFonteIndisponivelAviso('djen', 'timeout')]) as never,
    );

    const component = render(SavedConsultations);

    await waitFor(() => expect(component.getByText(/Não foi possível comparar/)).toBeTruthy());
    expect(component.queryByText(/Mudou desde/)).toBeNull();
  });

  it('removes the stored snapshot together with the saved consultation', async () => {
    saveItem();
    vi.mocked(processoCnj.buscarProcesso).mockResolvedValue(resultadoWith(3) as never);

    const component = render(SavedConsultations);
    await waitFor(() => expect(getConsultationSnapshot(ID)).not.toBeNull());

    await fireEvent.click(component.getByText('Remover'));

    await waitFor(() => expect(component.getByText('Nenhuma consulta salva ainda')).toBeTruthy());
    expect(getConsultationSnapshot(ID)).toBeNull();
  });
});
