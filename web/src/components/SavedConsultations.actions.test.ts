import { within } from '@testing-library/dom';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it } from 'vitest';
import SavedConsultations from './SavedConsultations.svelte';
import {
  SAVED_CONSULTATIONS_STORAGE_KEY,
  parseSavedConsultations,
  saveProcessConsultation,
  saveSearchConsultation,
  serializeSavedConsultations,
} from '../lib/savedConsultations';

const CNJ = '0000001-02.2024.8.22.0001';
const DIGITS = '00000010220248220001';

beforeEach(() => {
  localStorage.clear();
});

describe('SavedConsultations — recurring-use flow', () => {
  it('reopens a saved dossier and removes the local shortcut without affecting product access', async () => {
    const items = saveProcessConsultation([], CNJ, 'Caso teste', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));

    const component = render(SavedConsultations);

    const dossier = await waitFor(() => component.getByText('Abrir dossiê'));
    expect(dossier.getAttribute('href')).toContain('processo?cnj=0000001-02.2024.8.22.0001');

    await fireEvent.click(component.getByText('Remover'));

    await waitFor(() => expect(component.getByText('Nenhuma consulta salva ainda')).toBeTruthy());
    expect(parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY))).toEqual([]);
  });

  it('can create the local shortcut from the page and keeps only the canonical CNJ', async () => {
    const component = render(SavedConsultations);
    const cnjInput = await waitFor(() => component.getByLabelText('Adicionar processo'));
    const labelInput = component.getByLabelText('Apelido opcional da consulta');

    await fireEvent.input(cnjInput, { target: { value: CNJ } });
    await fireEvent.input(labelInput, { target: { value: 'Caso teste' } });
    await fireEvent.click(component.getByText('Salvar processo'));

    const saved = parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY));
    expect(saved).toHaveLength(1);
    expect(saved[0].type).toBe('processo');
    if (saved[0].type === 'processo') expect(saved[0].cnj).toBe(DIGITS);
    expect(saved[0].label).toBe('Caso teste');
  });

  it('reopens a saved DJEN search and removes it without touching a saved process', async () => {
    const withProcess = saveProcessConsultation([], CNJ, 'Caso teste', '2026-08-21T12:00:00.000Z');
    const items = saveSearchConsultation(
      withProcess,
      { siglaTribunal: 'TJRO', texto: 'contrato' },
      'Contratos TJRO',
      '2026-08-22T12:00:00.000Z',
    );
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));

    const component = render(SavedConsultations);

    const reopen = await waitFor(() => component.getByText('Reabrir busca'));
    const href = reopen.getAttribute('href') ?? '';
    expect(href).toContain('publicacoes?');
    expect(href).toContain('siglaTribunal=TJRO');
    expect(href).toContain('texto=contrato');

    const searchItem = within(reopen.closest('li')!);
    await fireEvent.click(searchItem.getByText('Remover'));

    const remaining = parseSavedConsultations(
      localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY),
    );
    expect(remaining).toHaveLength(1);
    expect(remaining[0].type).toBe('processo');
  });
});
