import { classifyCnjInput, formatCnj, normalizeCnj } from './processoCnj';

export const SAVED_CONSULTATIONS_STORAGE_KEY = 'causaganha:saved-consultations:v1';

export type SavedProcessConsultation = {
  id: string;
  type: 'processo';
  cnj: string;
  label: string;
  savedAt: string;
};

export type SavedConsultation = SavedProcessConsultation;

function isSavedProcess(value: unknown): value is SavedProcessConsultation {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<SavedProcessConsultation>;
  return (
    item.type === 'processo' &&
    typeof item.cnj === 'string' &&
    classifyCnjInput(item.cnj) === 'valid' &&
    typeof item.label === 'string' &&
    typeof item.savedAt === 'string'
  );
}

export function parseSavedConsultations(raw: string | null): SavedConsultation[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(isSavedProcess)
      .map((item) => {
        const cnj = normalizeCnj(item.cnj);
        return {
          ...item,
          id: `processo:${cnj}`,
          cnj,
          label: item.label.trim(),
        };
      })
      .sort((a, b) => b.savedAt.localeCompare(a.savedAt));
  } catch {
    return [];
  }
}

export function serializeSavedConsultations(items: SavedConsultation[]): string {
  return JSON.stringify(items);
}

export function saveProcessConsultation(
  items: SavedConsultation[],
  rawCnj: string,
  label = '',
  savedAt = new Date().toISOString(),
): SavedConsultation[] {
  if (classifyCnjInput(rawCnj) !== 'valid') {
    throw new Error('CNJ inválido');
  }

  const cnj = normalizeCnj(rawCnj);
  const id = `processo:${cnj}`;
  const existing = items.find((item) => item.id === id);
  const next: SavedProcessConsultation = {
    id,
    type: 'processo',
    cnj,
    label: label.trim() || existing?.label || formatCnj(cnj),
    savedAt: existing?.savedAt ?? savedAt,
  };

  return [next, ...items.filter((item) => item.id !== id)].sort((a, b) =>
    b.savedAt.localeCompare(a.savedAt),
  );
}

export function renameSavedConsultation(
  items: SavedConsultation[],
  id: string,
  label: string,
): SavedConsultation[] {
  const clean = label.trim();
  return items.map((item) =>
    item.id === id ? { ...item, label: clean || formatCnj(item.cnj) } : item,
  );
}

export function removeSavedConsultation(
  items: SavedConsultation[],
  id: string,
): SavedConsultation[] {
  return items.filter((item) => item.id !== id);
}
