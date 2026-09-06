import type { ConsultationSnapshot } from './consultationSnapshot';

export const CONSULTATION_SNAPSHOTS_STORAGE_KEY = 'causaganha:consultation-snapshots:v1';

type SnapshotsById = Record<string, ConsultationSnapshot>;

function readAll(): SnapshotsById {
  try {
    const raw = localStorage.getItem(CONSULTATION_SNAPSHOTS_STORAGE_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? (parsed as SnapshotsById) : {};
  } catch {
    return {};
  }
}

function writeAll(snapshots: SnapshotsById): void {
  localStorage.setItem(CONSULTATION_SNAPSHOTS_STORAGE_KEY, JSON.stringify(snapshots));
}

/** Última captura conhecida da consulta salva `id`, ou null se nunca capturada. */
export function getConsultationSnapshot(id: string): ConsultationSnapshot | null {
  return readAll()[id] ?? null;
}

/** Substitui a captura guardada para `id` pela mais recente. */
export function saveConsultationSnapshot(id: string, snapshot: ConsultationSnapshot): void {
  const all = readAll();
  all[id] = snapshot;
  writeAll(all);
}

/** Remove a captura de `id` — chamado junto da remoção da própria consulta salva. */
export function removeConsultationSnapshot(id: string): void {
  const all = readAll();
  if (!(id in all)) return;
  delete all[id];
  writeAll(all);
}
