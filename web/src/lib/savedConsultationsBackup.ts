import { parseSavedConsultationItems, type SavedConsultation } from './savedConsultations';

/** Bumped whenever the backup file *shape* changes (see #1235). */
export const SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION = 1;

type SavedConsultationsBackup = {
  schema_version: number;
  exported_at: string;
  items: SavedConsultation[];
};

export type ParseBackupResult =
  | { ok: true; items: SavedConsultation[] }
  | { ok: false; error: string };

export function serializeBackup(
  items: SavedConsultation[],
  exportedAt = new Date().toISOString(),
): string {
  const payload: SavedConsultationsBackup = {
    schema_version: SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION,
    exported_at: exportedAt,
    items,
  };
  return JSON.stringify(payload, null, 2);
}

/**
 * Parses an imported backup file. Deliberately stricter than
 * `parseSavedConsultations` (live storage): a bare array or a missing/wrong
 * `schema_version` is rejected outright rather than guessed at, so an
 * invalid or future-format file never partially applies (see #1235's
 * "importação transacional" criterion). Individual malformed *items* inside
 * an otherwise valid envelope are still dropped, not fatal — the same
 * tolerance `parseSavedConsultations` already has for live storage.
 */
export function parseBackup(raw: string): ParseBackupResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { ok: false, error: 'Arquivo não é um JSON válido.' };
  }

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { ok: false, error: 'Arquivo não é um backup do CausaGanha (formato inesperado).' };
  }

  const payload = parsed as Partial<SavedConsultationsBackup>;
  if (payload.schema_version !== SAVED_CONSULTATIONS_BACKUP_SCHEMA_VERSION) {
    return {
      ok: false,
      error: `Versão de backup não suportada (${String(payload.schema_version)}).`,
    };
  }
  if (!Array.isArray(payload.items)) {
    return { ok: false, error: 'Arquivo não contém uma lista de consultas.' };
  }

  return { ok: true, items: parseSavedConsultationItems(payload.items) };
}

/**
 * Merges an imported list into the current storage. Dedup identity is the
 * same canonical `id` every mutator in savedConsultations.ts already uses;
 * on a collision the existing item wins entirely (label, savedAt) — a
 * predictable rule that never lets an import silently rename something the
 * user already has (see #1235's "preservar rótulo existente de forma
 * previsível"). Only ids absent from `existing` are actually added.
 */
export function mergeSavedConsultations(
  existing: SavedConsultation[],
  imported: SavedConsultation[],
): SavedConsultation[] {
  const existingIds = new Set(existing.map((item) => item.id));
  const additions = imported.filter((item) => !existingIds.has(item.id));
  return [...existing, ...additions].sort((a, b) => b.savedAt.localeCompare(a.savedAt));
}
