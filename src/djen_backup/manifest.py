"""Manifest-driven sync state — single source of truth for all (tribunal, date) pairs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path  # noqa: TC003 — used at runtime in save/load methods
from typing import NamedTuple

import structlog


log = structlog.get_logger()

IA_STATE_ITEM = "causaganha-dashboard"
IA_MANIFEST_FILENAME = "sync-manifest.csv"
_IA_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_IA_S3_URL = f"https://s3.us.archive.org/{IA_STATE_ITEM}/{{}}"

HEADER = "tribunal,date,ia_status,djen_status,updated_at"


class ManifestCounts(NamedTuple):
    """Aggregate counts for progress display."""

    total: int
    uploaded: int
    available: int
    absent: int
    unknown: int


@dataclass
class ManifestEntry:
    """A single (tribunal, date) pair with its sync status."""

    tribunal: str
    date: date
    ia_status: str = ""  # "" (unknown) | "uploaded"
    djen_status: str = ""  # "" (unknown) | "available" | "absent"
    updated_at: str = ""


class SyncManifest:
    """The single source of truth for all (tribunal, date) pairs.

    Replaces both ZipInventory and SyncState.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ManifestEntry] = {}
        self._lock = asyncio.Lock()

    def __len__(self) -> int:
        """Return number of manifest entries."""
        return len(self._entries)

    @staticmethod
    def _key(tribunal: str, d: date) -> str:
        return f"{tribunal.upper()}/{d.isoformat()}"

    @staticmethod
    def _ia_url(tribunal: str, d: date) -> str:
        item_id = f"djen-{tribunal.lower()}-{d.year}"
        filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
        return f"https://archive.org/download/{item_id}/{filename}"

    # ── Build ────────────────────────────────────────────────────────

    def build(self, tribunals: list[str], start: date, end: date) -> int:
        """Phase 1: populate all (tribunal, date) weekday pairs.

        Only adds entries that don't already exist (preserves loaded state).
        Returns count of new entries added.
        """
        added = 0
        for t in tribunals:
            t_upper = t.upper()
            current = start
            while current <= end:
                if current.weekday() < 5:
                    k = self._key(t_upper, current)
                    if k not in self._entries:
                        self._entries[k] = ManifestEntry(tribunal=t_upper, date=current)
                        added += 1
                current += timedelta(days=1)
        return added

    def prune(self) -> int:
        """Remove weekend entries (unless already uploaded). Returns count removed."""
        to_remove = [
            k for k, e in self._entries.items()
            if e.date.weekday() >= 5 and e.ia_status != "uploaded"
        ]
        for k in to_remove:
            del self._entries[k]
        return len(to_remove)

    # ── Mark methods (async, lock-protected) ─────────────────────────

    async def mark_ia_uploaded(self, tribunal: str, dates: set[date]) -> int:
        """Bulk-mark dates as uploaded on IA. Returns count changed."""
        now = datetime.now(UTC).isoformat(timespec="seconds")
        changed = 0
        async with self._lock:
            for d in dates:
                k = self._key(tribunal, d)
                entry = self._entries.get(k)
                if entry and entry.ia_status != "uploaded":
                    entry.ia_status = "uploaded"
                    entry.updated_at = now
                    changed += 1
        return changed

    async def mark_ia_checked(self, tribunal: str, year: int, found_dates: set[date]) -> None:
        """After fetching IA metadata for a tribunal+year, mark found as uploaded.

        Does NOT mark missing ones — they stay unknown for ia_status
        (they might exist but not be in metadata yet).
        """
        await self.mark_ia_uploaded(tribunal, found_dates)

    async def mark_djen_available(self, tribunal: str, d: date) -> None:
        async with self._lock:
            k = self._key(tribunal, d)
            entry = self._entries.get(k)
            if entry:
                entry.djen_status = "available"
                entry.updated_at = datetime.now(UTC).isoformat(timespec="seconds")

    async def mark_djen_absent(self, tribunal: str, d: date) -> None:
        async with self._lock:
            k = self._key(tribunal, d)
            entry = self._entries.get(k)
            if entry:
                entry.djen_status = "absent"
                entry.updated_at = datetime.now(UTC).isoformat(timespec="seconds")

    async def mark_uploaded(self, tribunal: str, d: date) -> None:
        """After successful upload to IA."""
        async with self._lock:
            k = self._key(tribunal, d)
            entry = self._entries.get(k)
            if entry:
                entry.ia_status = "uploaded"
                entry.updated_at = datetime.now(UTC).isoformat(timespec="seconds")

    # ── Query methods ────────────────────────────────────────────────

    def has_uploaded_entries(self, tribunal: str, year: int) -> bool:
        """Check if any entries for this tribunal+year are already marked uploaded."""
        t_upper = tribunal.upper()
        return any(
            e.tribunal == t_upper and e.date.year == year and e.ia_status == "uploaded"
            for e in self._entries.values()
        )

    def counts(self) -> ManifestCounts:
        uploaded = 0
        available = 0
        absent = 0
        unknown = 0
        for e in self._entries.values():
            if e.ia_status == "uploaded":
                uploaded += 1
            elif e.djen_status == "available":
                available += 1
            elif e.djen_status == "absent":
                absent += 1
            else:
                unknown += 1
        return ManifestCounts(
            total=len(self._entries),
            uploaded=uploaded,
            available=available,
            absent=absent,
            unknown=unknown,
        )

    def items_needing_ia_check(self) -> list[tuple[str, int]]:
        """Return (tribunal, year) pairs that have fully unknown entries.

        An entry is fully unknown when both ia_status and djen_status are empty.
        If djen_status is already set, the IA check was already done for that item.
        """
        pairs: set[tuple[str, int]] = set()
        for e in self._entries.values():
            if e.ia_status == "" and e.djen_status == "":
                pairs.add((e.tribunal, e.date.year))
        return sorted(pairs, key=lambda p: (-p[1], p[0]))

    def entries_needing_djen_check(self, tribunal: str, year: int) -> list[ManifestEntry]:
        """Entries where ia!=uploaded and djen=unknown for a given tribunal+year."""
        result = []
        t_upper = tribunal.upper()
        for e in self._entries.values():
            if (
                e.tribunal == t_upper
                and e.date.year == year
                and e.ia_status != "uploaded"
                and e.djen_status == ""
            ):
                result.append(e)
        result.sort(key=lambda e: e.date, reverse=True)
        return result

    def entries_needing_upload(self) -> list[ManifestEntry]:
        """Entries where djen=available and ia!=uploaded, interleaved by tribunal.

        Round-robins across tribunals so download workers spread across
        different tribunals rather than draining one tribunal at a time.
        """
        from itertools import zip_longest

        by_tribunal: dict[str, list[ManifestEntry]] = {}
        for e in self._entries.values():
            if e.djen_status == "available" and e.ia_status != "uploaded":
                by_tribunal.setdefault(e.tribunal, []).append(e)

        # Sort each tribunal's entries by date descending (most recent first)
        for entries in by_tribunal.values():
            entries.sort(key=lambda e: e.date, reverse=True)

        # Interleave: one from each tribunal in turn
        result: list[ManifestEntry] = []
        for batch in zip_longest(*by_tribunal.values()):
            for entry in batch:
                if entry is not None:
                    result.append(entry)
        return result

    def get_status(self, tribunal: str, d: date) -> ManifestEntry | None:
        return self._entries.get(self._key(tribunal, d))

    # ── CSV serialization ────────────────────────────────────────────

    def to_csv(self) -> str:
        lines = [HEADER]
        rows = sorted(self._entries.values(), key=lambda e: (e.tribunal, e.date))
        for e in rows:
            lines.append(
                f"{e.tribunal},{e.date.isoformat()},{e.ia_status},{e.djen_status},"
                f"{e.updated_at}"
            )
        return "\n".join(lines) + "\n"

    def load_from_csv(self, text: str, *, overwrite: bool = False) -> int:
        """Load from CSV text. Supports both new manifest format and legacy zip-inventory format.

        When ``overwrite=True``, existing entries are fully replaced by loaded
        values (use for local disk which is always the freshest source).
        When ``overwrite=False`` (default), merges keeping the more advanced status
        (use for IA which may have entries from other runners).

        Returns count of entries added/updated.
        """
        before = len(self._entries)
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith(("tribunal", "timestamp")):
                continue

            parts = line.split(",")

            # Detect legacy format: timestamp,tribunal,date,status,url
            if len(parts) >= 4 and "T" in parts[0] and parts[0][0].isdigit():
                self._load_legacy_line(parts)
            elif len(parts) >= 4:
                self._load_manifest_line(parts, overwrite=overwrite)

        return len(self._entries) - before

    def _load_legacy_line(self, parts: list[str]) -> None:
        """Parse old zip-inventory.txt format: timestamp,tribunal,date,status,url.

        Only trusts ``uploaded`` — the file physically exists on IA.
        Ignores ``absent`` and ``staged`` (our own unverified claims).
        """
        ts = parts[0]
        tribunal = parts[1].upper()
        date_str = parts[2]
        status = parts[3]
        if status != "uploaded":
            return
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            return

        k = self._key(tribunal, d)
        existing = self._entries.get(k)

        if existing:
            if existing.ia_status != "uploaded":
                existing.ia_status = "uploaded"
                existing.updated_at = ts
        else:
            self._entries[k] = ManifestEntry(
                tribunal=tribunal, date=d, ia_status="uploaded", updated_at=ts
            )

    def _load_manifest_line(self, parts: list[str], *, overwrite: bool = False) -> None:
        """Parse new manifest format: tribunal,date,ia_status,djen_status,updated_at.

        In merge mode (overwrite=False, used for IA): only trusts ``ia_status=uploaded``
        (file physically exists on IA). Ignores ``djen_status=absent`` — that's our own
        unverified claim that may be wrong.

        In overwrite mode (used for local disk): trusts everything — local is always
        the freshest source, including intentional resets.
        """
        tribunal = parts[0].upper()
        try:
            d = date.fromisoformat(parts[1])
        except ValueError:
            return

        ia_status = parts[2] if len(parts) > 2 else ""
        djen_status = parts[3] if len(parts) > 3 else ""
        # Support both old 6-column (with djen_url) and new 5-column format
        updated_at = parts[5] if len(parts) > 5 else (parts[4] if len(parts) > 4 else "")

        k = self._key(tribunal, d)
        existing = self._entries.get(k)

        if existing and overwrite:
            existing.ia_status = ia_status
            existing.djen_status = djen_status
            existing.updated_at = updated_at
        elif existing:
            # Merge: only trust uploaded (verified fact)
            if ia_status == "uploaded" and existing.ia_status != "uploaded":
                existing.ia_status = "uploaded"
                existing.updated_at = updated_at or existing.updated_at
        else:
            # New entry from IA: only keep uploaded, discard absent claims
            if not overwrite:
                djen_status = "" if djen_status == "absent" else djen_status
            self._entries[k] = ManifestEntry(
                tribunal=tribunal,
                date=d,
                ia_status=ia_status,
                djen_status=djen_status,
                updated_at=updated_at,
            )

    # ── Disk persistence ─────────────────────────────────────────────

    def save_to_disk(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_csv(), encoding="utf-8")
        log.info("manifest_saved_to_disk", path=str(path), entries=len(self._entries))

    def load_from_disk(self, path: Path) -> int:
        """Load from local disk. Overwrites existing entries (local is always fresher)."""
        if not path.exists():
            return 0
        count = self.load_from_csv(path.read_text(encoding="utf-8"), overwrite=True)
        log.info("manifest_loaded_from_disk", path=str(path), loaded=count)
        return count

    # ── IA persistence ───────────────────────────────────────────────

    async def load_from_ia(self) -> int:
        """Download manifest from IA. Falls back to legacy zip-inventory.txt."""
        import httpx

        # Try new manifest first
        for filename in (IA_MANIFEST_FILENAME, "zip-inventory.txt"):
            url = _IA_DOWNLOAD_URL.format(filename)
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        count = self.load_from_csv(resp.text)
                        log.info(
                            "manifest_loaded_from_ia",
                            filename=filename,
                            size=len(resp.text),
                            loaded=count,
                        )
                        return count
            except Exception as exc:
                log.warning("manifest_download_failed", filename=filename, error=str(exc))
        return 0

    async def upload_to_ia(self, auth: str) -> bool:
        """Merge-then-upload: re-download remote, merge, upload."""
        import httpx

        from djen_backup.archive import put_ia_bytes

        # Re-download and merge to prevent race conditions
        url_dl = _IA_DOWNLOAD_URL.format(IA_MANIFEST_FILENAME)
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(url_dl)
                if resp.status_code == 200:
                    self.load_from_csv(resp.text)
        except Exception as exc:
            log.warning("manifest_merge_download_failed", error=str(exc))

        url_up = _IA_S3_URL.format(IA_MANIFEST_FILENAME)
        content = self.to_csv().encode("utf-8")
        headers = {
            "Authorization": auth,
            "Content-Type": "text/csv",
            "x-amz-auto-make-bucket": "1",
            "x-archive-meta-mediatype": "data",
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await put_ia_bytes(client, url_up, content, headers)
                if resp.status_code < 400:
                    log.info("manifest_uploaded_to_ia", entries=len(self._entries))
                    return True
                log.warning("manifest_upload_failed", status=resp.status_code)
        except Exception as exc:
            log.warning("manifest_upload_error", error=str(exc))
        return False
