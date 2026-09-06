import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SavedConsultations from './SavedConsultations.svelte';
import {
  SAVED_CONSULTATIONS_STORAGE_KEY,
  parseSavedConsultations,
  saveProcessConsultation,
  serializeSavedConsultations,
} from '../lib/savedConsultations';
import { SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION } from '../lib/savedConsultationsBackup';

const CNJ_A = '0000001-02.2024.8.22.0001';
const CNJ_B = '0000002-03.2024.8.22.0001';

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe('SavedConsultations — export (#1235)', () => {
  it('downloads a versioned backup file containing exactly the saved items', async () => {
    const items = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));

    let capturedParts: unknown[] | null = null;
    let downloadName: string | null = null;
    const OriginalBlob = globalThis.Blob;
    vi.stubGlobal(
      'Blob',
      class extends OriginalBlob {
        constructor(parts: unknown[], opts?: BlobPropertyBag) {
          super(parts as BlobPart[], opts);
          capturedParts = parts;
        }
      },
    );
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => 'blob:mock-url');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      downloadName = this.download;
    });

    const component = render(SavedConsultations);
    const exportButton = await waitFor(() => component.getByText('Exportar salvos'));
    await fireEvent.click(exportButton);

    expect(downloadName).toMatch(/\.json$/);
    expect(capturedParts).not.toBeNull();
    const text = (capturedParts as unknown as string[]).join('');
    const parsed = JSON.parse(text);
    expect(parsed.schema_version).toBe(SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION);
    expect(parsed.items).toEqual(items);
  });

  it('is reachable and activatable from the keyboard alone', async () => {
    const items = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));

    const component = render(SavedConsultations);
    const exportButton = (await waitFor(() =>
      component.getByText('Exportar salvos'),
    )) as HTMLElement;

    exportButton.focus();
    expect(exportButton).toHaveFocus();
  });
});

describe('SavedConsultations — import (#1235)', () => {
  function makeFile(content: string, name = 'backup.json') {
    return new File([content], name, { type: 'application/json' });
  }

  it('merges a valid backup into empty storage and persists it', async () => {
    const backupItems = saveProcessConsultation([], CNJ_A, 'Caso importado', '2026-08-20T12:00:00.000Z');
    const raw = JSON.stringify({
      schema_version: SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION,
      exported_at: '2026-09-06T21:00:00.000Z',
      items: backupItems,
    });

    const component = render(SavedConsultations);
    await waitFor(() => component.getByText('Nenhuma consulta salva ainda'));

    const input = component.container.querySelector('input[type="file"]') as HTMLInputElement;
    await fireEvent.change(input, { target: { files: [makeFile(raw)] } });

    await waitFor(() => expect(component.getByText('Caso importado')).toBeTruthy());
    expect(parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY))).toEqual(
      backupItems,
    );
  });

  it('keeps the existing label on a collision and adds genuinely new items', async () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Nome local', '2026-08-20T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(existing));

    const importedSameId = saveProcessConsultation([], CNJ_A, 'Nome do backup', '2026-08-25T12:00:00.000Z');
    const importedBoth = saveProcessConsultation(importedSameId, CNJ_B, 'Caso novo', '2026-08-26T12:00:00.000Z');
    const raw = JSON.stringify({
      schema_version: SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION,
      exported_at: '2026-09-06T21:00:00.000Z',
      items: importedBoth,
    });

    const component = render(SavedConsultations);
    await waitFor(() => component.getByText('Nome local'));

    const input = component.container.querySelector('input[type="file"]') as HTMLInputElement;
    await fireEvent.change(input, { target: { files: [makeFile(raw)] } });

    await waitFor(() => expect(component.getByText('Caso novo')).toBeTruthy());
    expect(component.getByText('Nome local')).toBeTruthy();
    expect(component.queryByText('Nome do backup')).toBeNull();
  });

  it('rejects an invalid file without changing existing storage', async () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(existing));

    const component = render(SavedConsultations);
    await waitFor(() => component.getByText('Caso A'));

    const input = component.container.querySelector('input[type="file"]') as HTMLInputElement;
    await fireEvent.change(input, { target: { files: [makeFile('{ not json')] } });

    await waitFor(() => expect(component.getByRole('alert')).toBeTruthy());
    expect(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY)).toBe(
      serializeSavedConsultations(existing),
    );
    expect(component.getByText('Caso A')).toBeTruthy();
  });

  it('rejects an unknown schema_version without changing existing storage', async () => {
    const existing = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(existing));
    const raw = JSON.stringify({ schema_version: 999, exported_at: 'x', items: [] });

    const component = render(SavedConsultations);
    await waitFor(() => component.getByText('Caso A'));

    const input = component.container.querySelector('input[type="file"]') as HTMLInputElement;
    await fireEvent.change(input, { target: { files: [makeFile(raw)] } });

    await waitFor(() => expect(component.getByRole('alert')).toBeTruthy());
    expect(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY)).toBe(
      serializeSavedConsultations(existing),
    );
  });

  it('is reachable and activatable from the keyboard alone', async () => {
    const component = render(SavedConsultations);
    const importButton = (await waitFor(() =>
      component.getByText('Importar salvos'),
    )) as HTMLElement;

    importButton.focus();
    expect(importButton).toHaveFocus();
  });
});
