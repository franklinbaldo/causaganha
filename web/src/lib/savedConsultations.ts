import { classifyCnjInput, formatCnj, normalizeCnj } from './processoCnj';
import { hasAnyQueryValue, queryToSearchParams } from './searchQueryString';
import type { DjenComunicacaoQuery } from './djen';

export const SAVED_CONSULTATIONS_STORAGE_KEY = 'causaganha:saved-consultations:v1';

/**
 * Bumped whenever the persisted payload *shape* changes (not per-field
 * additions, which parseSavedConsultations already tolerates). Every
 * existing user's storage today is a bare array with no version marker
 * at all — that shape is read as the implicit predecessor of version 1.
 */
export const SAVED_CONSULTATIONS_SCHEMA_VERSION = 1;

type SavedConsultationsPayload = { version: number; items: unknown[] };

function isVersionedPayload(value: unknown): value is SavedConsultationsPayload {
  return (
    !!value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    Array.isArray((value as SavedConsultationsPayload).items)
  );
}

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

// `label` was added to the schema after `type`/`cnj`/`params`/`savedAt` — a
// stored record predating it is a legacy shape to migrate forward with a
// derived label, not a malformed one to discard (see #908).
function isSavedProcess(value: unknown): value is Omit<SavedProcessConsultation, 'label'> & { label?: string } {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<SavedProcessConsultation>;
  return (
    item.type === 'processo' &&
    typeof item.cnj === 'string' &&
    classifyCnjInput(item.cnj) === 'valid' &&
    (item.label === undefined || typeof item.label === 'string') &&
    typeof item.savedAt === 'string'
  );
}

function isSavedSearch(value: unknown): value is Omit<SavedSearchConsultation, 'label'> & { label?: string } {
  if (!value || typeof value !== 'object') return false;
  const item = value as Partial<SavedSearchConsultation>;
  return (
    item.type === 'busca' &&
    typeof item.params === 'string' &&
    item.params.length > 0 &&
    (item.label === undefined || typeof item.label === 'string') &&
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
    const rawItems = Array.isArray(parsed) ? parsed : isVersionedPayload(parsed) ? parsed.items : null;
    if (!rawItems) return [];
    return rawItems
      .map((item): SavedConsultation | null => {
        if (isSavedProcess(item)) {
          const cnj = normalizeCnj(item.cnj);
          const label = item.label?.trim() || formatCnj(cnj);
          return { ...item, id: `processo:${cnj}`, cnj, label };
        }
        if (isSavedSearch(item)) {
          const label = item.label?.trim() || 'Busca DJEN';
          return { ...item, id: `busca:${item.params}`, label };
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
  const payload: SavedConsultationsPayload = { version: SAVED_CONSULTATIONS_SCHEMA_VERSION, items };
  return JSON.stringify(payload);
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
