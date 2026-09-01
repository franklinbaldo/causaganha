import { within } from '@testing-library/dom';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it } from 'vitest';
import SavedConsultations from './SavedConsultations.svelte';
import {
  SAVED_CONSULTATIONS_STORAGE_KEY,
  saveProcessConsultation,
  serializeSavedConsultations,
} from '../lib/savedConsultations';

const CNJ_A = '0000001-02.2024.8.22.0001';
const CNJ_B = '0000002-03.2024.8.22.0001';

beforeEach(() => {
  localStorage.clear();
});

describe('SavedConsultations — keyboard and focus (#908)', () => {
  it('keeps a "Remover" button reachable and activatable from the keyboard alone', async () => {
    const items = saveProcessConsultation([], CNJ_A, 'Caso teste', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));

    const component = render(SavedConsultations);
    const removeButton = (await waitFor(() => component.getByText('Remover'))) as HTMLElement;

    removeButton.focus();
    expect(removeButton).toHaveFocus();
  });

  it('does not strand focus on <body> after removing the only item via keyboard', async () => {
    const items = saveProcessConsultation([], CNJ_A, 'Caso teste', '2026-08-21T12:00:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(items));

    const component = render(SavedConsultations);
    const removeButton = (await waitFor(() => component.getByText('Remover'))) as HTMLElement;

    removeButton.focus();
    await fireEvent.click(removeButton);

    await waitFor(() => expect(component.getByText('Nenhuma consulta salva ainda')).toBeTruthy());
    expect(document.activeElement).not.toBe(document.body);
  });

  it('moves focus to the remaining item\'s "Remover" button after removing the first one via keyboard', async () => {
    // saveProcessConsultation sorts newest-first, so "Caso B" (saved later) renders before "Caso A".
    const withA = saveProcessConsultation([], CNJ_A, 'Caso A', '2026-08-21T12:00:00.000Z');
    const withBoth = saveProcessConsultation(withA, CNJ_B, 'Caso B', '2026-08-21T12:01:00.000Z');
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(withBoth));

    const component = render(SavedConsultations);
    await waitFor(() => component.getByText('Caso A'));

    const firstItem = component.getByText('Caso B').closest('li')!;
    const firstRemoveButton = within(firstItem).getByText('Remover') as HTMLElement;
    firstRemoveButton.focus();
    await fireEvent.click(firstRemoveButton);

    await waitFor(() => expect(component.queryByText('Caso B')).toBeNull());
    const remainingItem = component.getByText('Caso A').closest('li')!;
    const remainingRemoveButton = within(remainingItem).getByText('Remover') as HTMLElement;
    expect(remainingRemoveButton).toHaveFocus();
  });
});
