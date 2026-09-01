import { classifyCnjInput, formatCnj, normalizeCnj } from './processoCnj';
import { hasAnyQueryValue, queryToSearchParams } from './searchQueryString';
import type { DjenComunicacaoQuery } from './djen';

export const SAVED_CONSULTATIONS_STORAGE_KEY = 'causaganha:saved-consultations:v1';

export type SavedProcessConsultation = {
  id: string;
  type: 'processo';
  cnj: string;
  label: string;
  savedAt: string;
};

export type SavedSearchConsultation = {
  id: string;
  type: 'busca';
  /** Canonical, sorted URL query string (no `pagina`) — also the dedup identity. */
  params: string;
  label: string;
  savedAt: string;
};

export type SavedConsultation = SavedProcessConsultation | SavedSearchConsultation;

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

function isSavedSearch(value: unknown): value is SavedSearchConsultation {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<SavedSearchConsultation>;
  return (
    item.type === 'busca' &&
    typeof item.params === 'string' &&
    item.params.length > 0 &&
    typeof item.label === 'string' &&
    typeof item.savedAt === 'string'
  );
}

/** Sorted, `pagina`-less query string — identity for dedup and storage. */
function canonicalSearchParams(query: DjenComunicacaoQuery): string {
  const params = queryToSearchParams({ ...query, pagina: undefined });
  return new URLSearchParams([...params.entries()].sort(([a], [b]) => a.localeCompare(b))).toString();
}

export function searchConsultationId(query: DjenComunicacaoQuery): string {
  return `busca:${canonicalSearchParams(query)}`;
}

export function parseSavedConsultations(raw: string | null): SavedConsultation[] {
  if (!raw) return [];
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item): SavedConsultation | null => {
        if (isSavedProcess(item)) {
          const cnj = normalizeCnj(item.cnj);
          return { ...item, id: `processo:${cnj}`, cnj, label: item.label.trim() };
        }
        if (isSavedSearch(item)) {
          return { ...item, id: `busca:${item.params}`, label: item.label.trim() };
        }
        return null;
      })
      .filter((item): item is SavedConsultation => item !== null)
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

export function saveSearchConsultation(
  items: SavedConsultation[],
  query: DjenComunicacaoQuery,
  label = '',
  savedAt = new Date().toISOString(),
): SavedConsultation[] {
  if (!hasAnyQueryValue({ ...query, pagina: undefined, itensPorPagina: undefined })) {
    throw new Error('Busca vazia não pode ser salva');
  }

  const id = searchConsultationId(query);
  const params = canonicalSearchParams(query);
  const existing = items.find((item) => item.id === id) as SavedSearchConsultation | undefined;
  const next: SavedSearchConsultation = {
    id,
    type: 'busca',
    params,
    label: label.trim() || existing?.label || 'Busca DJEN',
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
  if (!clean) return items;
  return items.map((item) => (item.id === id ? { ...item, label: clean } : item));
}

export function removeSavedConsultation(
  items: SavedConsultation[],
  id: string,
): SavedConsultation[] {
  return items.filter((item) => item.id !== id);
}
