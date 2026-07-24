"""Manifest-driven sync state — single source of truth for all (tribunal, date) pairs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, NamedTuple


if TYPE_CHECKING:
    from pathlib import Path

import anyio
import httpx
import structlog


log = structlog.get_logger()

IA_STATE_ITEM = "causaganha-dashboard"
IA_PARQUET_FILENAME = "sync-manifest.parquet"
_IA_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_IA_S3_URL = f"https://s3.us.archive.org/{IA_STATE_ITEM}/{{}}"
_IA_FILES_METADATA_URL = f"https://archive.org/metadata/{IA_STATE_ITEM}/files"

HEADER = "tribunal,date,ia_status,djen_status,djen_raw,updated_at"


# ── DJEN status interpretation ───────────────────────────────────────
# djen_raw stores the actual response code/reason. We derive djen_status
# from it via interpret_djen_raw() — lets us reclassify later without
# re-querying DJEN.

# Codes we consider "truly absent" (no data will ever be there)
ABSENT_CODES = {"404", "400", "no_publications"}
# Codes we consider transient/retriable (should re-check)
TRANSIENT_CODES = {"403", "500", "502", "503", "504", "timeout", "network"}


def interpret_djen_raw(djen_raw: str) -> str:
    """Derive djen_status from djen_raw. Returns 'available', 'absent', or ''."""
    if not djen_raw:
        return ""
    if djen_raw == "200" or djen_raw.startswith("200:"):
        return "available"
    if djen_raw in ABSENT_CODES:
        return "absent"
    # Everything else (403, 5xx, timeouts, etc.) — transient, leave unknown
    return ""


def _raise_unless_ok(status_code: int, filename: str) -> None:
    """Raise when an IA download did not return HTTP 200 (satisfies TRY301)."""
    if status_code != 200:
        msg = f"IA download of {filename} returned HTTP {status_code}"
        raise RuntimeError(msg)


def _read_parquet_rows(path: str) -> list[tuple]:
    """Read all manifest rows from a local parquet file (runs in a thread)."""
    import duckdb

    con = duckdb.connect()
    try:
        return con.execute(
            "SELECT tribunal, date, ia_status, djen_status, djen_raw, updated_at"
            " FROM read_parquet(?)",
            [path],
        ).fetchall()
    finally:
        con.close()


def load_materialized_manifest(parquet_path: Path, segment_dir: Path) -> "SyncManifest":
    """Load a local manifest materialization and its pending event segments.

    This is the synchronous counterpart to :meth:`SyncManifest.load_from_ia`.
    Consumers that have downloaded the dashboard state must use it rather than
    reconstructing the retired CSV: the base parquet is replayed first and
    lexically ordered, un-compacted segments are then applied with the same
    field-level last-write-wins rules as the IA reader.
    """
    manifest = SyncManifest()
    if parquet_path.exists():
        for tribunal, d, ia_status, djen_status, djen_raw, updated_at in _read_parquet_rows(
            str(parquet_path)
        ):
            manifest.apply_event(
                tribunal,
                d,
                ia_status=ia_status or "",
                djen_status=djen_status or "",
                djen_raw=djen_raw or "",
                updated_at=updated_at or "",
            )
    for segment_path in sorted(segment_dir.glob("*.csv")) if segment_dir.exists() else []:
        manifest.apply_segment_csv(segment_path.read_text(encoding="utf-8"))
    return manifest


class ManifestCounts(NamedTuple):
    """Aggregate counts for progress display."""

    total: int
    uploaded: int
    available: int
    absent: int
    unknown: int
    ultima_atualizacao: str = ""


@dataclass
class ManifestEntry:
    """A single (tribunal, date) pair with its sync status.

    djen_raw stores the raw DJEN response (HTTP code or error tag).
    djen_status is derived from djen_raw via interpret_djen_raw().
    """

    tribunal: str
    date: date
    ia_status: str = ""  # "" (unknown) | "uploaded"
    djen_status: str = ""  # "" (unknown) | "available" | "absent"
    djen_raw: str = ""  # raw response: "200", "404", "403", "500", "timeout", etc.
    updated_at: str = ""


class SyncManifest:
    """The single source of truth for all (tribunal, date) pairs.

    Replaces both ZipInventory and SyncState.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ManifestEntry] = {}
        self._lock = asyncio.Lock()
        # Maintained tally — updated incrementally by mark_* (O(1) per mark).
        # Populated lazily on first counts() call; bulk operations (build,
        # prune, load_*) reset to None to force a full rebuild.
        self._counts_tally: dict[str, int] | None = None
        # Latest entry updated_at, cached alongside _counts_tally (same
        # rebuild-on-counts()/invalidate-on-mutation lifecycle) so exposing
        # it doesn't reintroduce the O(N)-per-call cost the tally cache
        # exists to avoid.
        self._latest_updated_at: str | None = None
        # Cache of (tribunal, year) pairs that have uploaded entries
        self._uploaded_items: set[tuple[str, int]] | None = None
        # Keys mutated by mark_* since the last successful segment flush.
        # Loads (parquet/CSV/segments) never dirty entries — only fresh
        # observations do. Phase 2: persistence emits only these rows as an
        # immutable manifest-log/ segment instead of rewriting the CSV.
        self._dirty: set[str] = set()
        self._run_id: str | None = None

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
        if added:
            self._invalidate_caches()
        return added

    @staticmethod
    def _categorize(entry: ManifestEntry) -> str:
        """Bucket an entry into uploaded/available/absent/unknown."""
        if entry.ia_status == "uploaded":
            return "uploaded"
        if entry.djen_status == "available":
            return "available"
        if entry.djen_status == "absent":
            return "absent"
        return "unknown"

    def _adjust_counts(self, old_cat: str, new_cat: str) -> None:
        """Incrementally adjust the maintained tally (no-op if not built yet)."""
        if self._counts_tally is None:
            return
        if old_cat == new_cat:
            return
        self._counts_tally[old_cat] -= 1
        self._counts_tally[new_cat] += 1

    def _track_uploaded(self, tribunal: str, year: int) -> None:
        """Incrementally add (tribunal, year) to the uploaded-items index.

        No-op if the index hasn't been built yet — it'll be populated on
        the first ``has_uploaded_entries`` call.
        """
        if self._uploaded_items is None:
            return
        self._uploaded_items.add((tribunal.upper(), year))

    def _invalidate_caches(self) -> None:
        # Force a full rebuild on next counts() / has_uploaded_entries() call.
        self._counts_tally = None
        self._latest_updated_at = None
        self._uploaded_items = None

    def _track_latest_updated_at(self, updated_at: str) -> None:
        """Incrementally extend the cached latest updated_at (no-op if not built yet)."""
        if self._counts_tally is None:
            return
        if self._latest_updated_at is None or updated_at > self._latest_updated_at:
            self._latest_updated_at = updated_at

    def prune(self) -> int:
        """Remove weekend entries (unless already uploaded). Returns count removed."""
        to_remove = [
            k
            for k, e in self._entries.items()
            if e.date.weekday() >= 5 and e.ia_status != "uploaded"
        ]
        for k in to_remove:
            del self._entries[k]
        if to_remove:
            self._invalidate_caches()
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
                    old_cat = self._categorize(entry)
                    entry.ia_status = "uploaded"
                    entry.updated_at = now
                    self._adjust_counts(old_cat, "uploaded")
                    self._track_uploaded(tribunal, d.year)
                    self._track_latest_updated_at(now)
                    self._dirty.add(k)
                    changed += 1
        return changed

    async def mark_ia_checked(self, tribunal: str, year: int, found_dates: set[date]) -> None:
        """After fetching IA metadata for a tribunal+year, mark found as uploaded."""
        await self.mark_ia_uploaded(tribunal, found_dates)

    async def mark_djen_raw(self, tribunal: str, d: date, raw: str) -> None:
        """Record raw DJEN response and derive djen_status from it."""
        async with self._lock:
            k = self._key(tribunal, d)
            entry = self._entries.get(k)
            if entry:
                old_cat = self._categorize(entry)
                entry.djen_raw = raw
                entry.djen_status = interpret_djen_raw(raw)
                entry.updated_at = datetime.now(UTC).isoformat(timespec="seconds")
                self._adjust_counts(old_cat, self._categorize(entry))
                self._track_latest_updated_at(entry.updated_at)
                self._dirty.add(k)

    async def mark_djen_available(self, tribunal: str, d: date) -> None:
        """Shortcut: mark djen_raw=200 → status=available."""
        await self.mark_djen_raw(tribunal, d, "200")

    async def mark_djen_absent(self, tribunal: str, d: date) -> None:
        """Shortcut: mark djen_raw=404 → status=absent."""
        await self.mark_djen_raw(tribunal, d, "404")

    async def mark_uploaded(self, tribunal: str, d: date) -> None:
        """After successful upload to IA."""
        async with self._lock:
            k = self._key(tribunal, d)
            entry = self._entries.get(k)
            if entry and entry.ia_status != "uploaded":
                old_cat = self._categorize(entry)
                entry.ia_status = "uploaded"
                entry.updated_at = datetime.now(UTC).isoformat(timespec="seconds")
                self._adjust_counts(old_cat, "uploaded")
                self._track_uploaded(tribunal, d.year)
                self._track_latest_updated_at(entry.updated_at)
                self._dirty.add(k)

    # ── Query methods ────────────────────────────────────────────────

    def has_uploaded_entries(self, tribunal: str, year: int) -> bool:
        """Check if any entries for this tribunal+year are already marked uploaded."""
        if self._uploaded_items is None:
            self._uploaded_items = {
                (e.tribunal, e.date.year)
                for e in self._entries.values()
                if e.ia_status == "uploaded"
            }
        return (tribunal.upper(), year) in self._uploaded_items

    def counts(self) -> ManifestCounts:
        """Return aggregate counts. O(1) when tally is warm, O(N) on rebuild."""
        if self._counts_tally is None:
            tally = {"uploaded": 0, "available": 0, "absent": 0, "unknown": 0}
            latest = ""
            for e in self._entries.values():
                tally[self._categorize(e)] += 1
                if e.updated_at and e.updated_at > latest:
                    latest = e.updated_at
            self._counts_tally = tally
            self._latest_updated_at = latest
        t = self._counts_tally
        return ManifestCounts(
            total=len(self._entries),
            uploaded=t["uploaded"],
            available=t["available"],
            absent=t["absent"],
            unknown=t["unknown"],
            ultima_atualizacao=self._latest_updated_at or "",
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
        """Entries where djen=available and ia!=uploaded, shuffled randomly.

        Shuffling distributes entries across different items (tribunal+year)
        so upload workers rarely collide on the same per-item lock.
        """
        import random

        result = [
            e
            for e in self._entries.values()
            if e.djen_status == "available" and e.ia_status != "uploaded"
        ]
        random.shuffle(result)
        return result

    def get_status(self, tribunal: str, d: date) -> ManifestEntry | None:
        return self._entries.get(self._key(tribunal, d))

    def to_summary(self) -> dict:
        """Generate compact summary for the webapp.

        Returns a dict with per-tribunal and per-year breakdowns,
        suitable for JSON serialization and client-side rendering.
        """
        from collections import defaultdict

        by_tribunal: dict[str, dict[str, int]] = defaultdict(
            lambda: {"uploaded": 0, "available": 0, "absent": 0, "unknown": 0, "total": 0}
        )
        by_year: dict[int, dict[str, int]] = defaultdict(
            lambda: {"uploaded": 0, "available": 0, "absent": 0, "unknown": 0, "total": 0}
        )
        # Per tribunal: earliest and latest uploaded dates
        tribunal_dates: dict[str, dict[str, str]] = defaultdict(
            lambda: {"earliest": "", "latest": ""}
        )

        for e in self._entries.values():
            if e.ia_status == "uploaded":
                cat = "uploaded"
            elif e.djen_status == "available":
                cat = "available"
            elif e.djen_status == "absent":
                cat = "absent"
            else:
                cat = "unknown"

            by_tribunal[e.tribunal][cat] += 1
            by_tribunal[e.tribunal]["total"] += 1
            by_year[e.date.year][cat] += 1
            by_year[e.date.year]["total"] += 1

            if e.ia_status == "uploaded":
                d_str = e.date.isoformat()
                td = tribunal_dates[e.tribunal]
                if not td["earliest"] or d_str < td["earliest"]:
                    td["earliest"] = d_str
                if not td["latest"] or d_str > td["latest"]:
                    td["latest"] = d_str

        counts = self.counts()

        tribunals_list = []
        for t in sorted(by_tribunal):
            s = by_tribunal[t]
            td = tribunal_dates.get(t, {"earliest": "", "latest": ""})
            pct = round(s["uploaded"] * 100 / s["total"], 1) if s["total"] else 0
            tribunals_list.append(
                {
                    "tribunal": t,
                    "uploaded": s["uploaded"],
                    "available": s["available"],
                    "absent": s["absent"],
                    "unknown": s["unknown"],
                    "total": s["total"],
                    "coverage_pct": pct,
                    "earliest_upload": td["earliest"],
                    "latest_upload": td["latest"],
                }
            )

        years_list = []
        for y in sorted(by_year):
            s = by_year[y]
            pct = round(s["uploaded"] * 100 / s["total"], 1) if s["total"] else 0
            years_list.append(
                {
                    "year": y,
                    "uploaded": s["uploaded"],
                    "available": s["available"],
                    "absent": s["absent"],
                    "unknown": s["unknown"],
                    "total": s["total"],
                    "coverage_pct": pct,
                }
            )

        return {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "totals": {
                "uploaded": counts.uploaded,
                "available": counts.available,
                "absent": counts.absent,
                "unknown": counts.unknown,
                "total": counts.total,
                "coverage_pct": round(counts.uploaded * 100 / counts.total, 1)
                if counts.total
                else 0,
            },
            "tribunals": tribunals_list,
            "years": years_list,
        }

    # ── CSV serialization ────────────────────────────────────────────

    def to_csv(self) -> str:
        lines = [HEADER]
        rows = sorted(self._entries.values(), key=lambda e: (e.tribunal, e.date))
        for e in rows:
            lines.append(
                f"{e.tribunal},{e.date.isoformat()},{e.ia_status},{e.djen_status},"
                f"{e.djen_raw},{e.updated_at}"
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

        loaded = len(self._entries) - before
        # Always invalidate: even when no entries were added, overwrite-mode
        # mutates existing entries' status which changes counts.
        self._invalidate_caches()
        return loaded

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
        """Parse manifest CSV format.

        Supports:
        - New 6-col: tribunal,date,ia_status,djen_status,djen_raw,updated_at
        - Old 5-col: tribunal,date,ia_status,djen_status,updated_at (no djen_raw)

        In merge mode (overwrite=False, used for IA): only trusts ``ia_status=uploaded``.
        In overwrite mode (used for local disk): trusts everything.
        """
        tribunal = parts[0].upper()
        try:
            d = date.fromisoformat(parts[1])
        except ValueError:
            return

        ia_status = parts[2] if len(parts) > 2 else ""
        djen_status = parts[3] if len(parts) > 3 else ""

        # Detect format by column count. Old formats lack djen_raw.
        if len(parts) >= 6:
            djen_raw = parts[4]
            updated_at = parts[5]
        else:
            # Old format — derive djen_raw from status if possible
            djen_raw = "200" if djen_status == "available" else ""
            updated_at = parts[4] if len(parts) > 4 else ""

        # Normalize legacy sentinel "error" → unknown so the row gets re-checked.
        # Older engine versions wrote a derived "error" string; canonical raw
        # values are HTTP codes or "timeout"/"network". See PR #677.
        if djen_raw == "error":
            djen_raw = ""
            djen_status = ""

        k = self._key(tribunal, d)
        existing = self._entries.get(k)

        if existing and overwrite:
            existing.ia_status = ia_status
            existing.djen_status = djen_status
            existing.djen_raw = djen_raw
            existing.updated_at = updated_at
        elif existing:
            # Merge: only trust uploaded (verified fact)
            if ia_status == "uploaded" and existing.ia_status != "uploaded":
                existing.ia_status = "uploaded"
                existing.updated_at = updated_at or existing.updated_at
        else:
            # New entry from IA: legacy bare ``djen_status="absent"`` (without
            # a djen_raw HTTP code) is the suspicious case CLAUDE.md flags —
            # rows from before djen_raw was canonical can't be re-verified.
            # Modern entries have djen_raw="404"/"400" alongside, and that IS
            # the canonical truth — keep it as-is. PR #677 found drain was
            # nuking 38k legitimate absent rows because this branch cleared
            # djen_raw whenever djen_status said absent.
            if not overwrite and djen_status == "absent" and not djen_raw:
                djen_status = ""
            self._entries[k] = ManifestEntry(
                tribunal=tribunal,
                date=d,
                djen_raw=djen_raw,
                ia_status=ia_status,
                djen_status=djen_status,
                updated_at=updated_at,
            )

    # ── Segment persistence (Phase 2, plan §4.2) ─────────────────────
    #
    # Writers no longer rewrite the canonical CSV on IA. Each flush emits
    # only the rows mutated since the previous flush (dirty tracking) as an
    # immutable, uniquely-named CSV segment under manifest-log/. The
    # compactor (scripts/render_manifest_parquet.py) absorbs segments into
    # the parquet base and prunes them.

    @property
    def dirty_count(self) -> int:
        """Number of entries mutated since the last successful segment flush."""
        return len(self._dirty)

    def _serialize_rows(self, keys: set[str]) -> str:
        from djen_backup.segments import SEGMENT_HEADER

        lines = [SEGMENT_HEADER]
        entries = sorted(
            (self._entries[k] for k in keys if k in self._entries),
            key=lambda e: (e.tribunal, e.date),
        )
        for e in entries:
            lines.append(
                f"{e.tribunal},{e.date.isoformat()},{e.ia_status},{e.djen_status},"
                f"{e.djen_raw},{e.updated_at}"
            )
        return "\n".join(lines) + "\n"

    def to_segment_csv(self) -> str:
        """Serialize only the dirty rows (header + mutated entries)."""
        return self._serialize_rows(set(self._dirty))

    async def upload_segment_to_ia(self, auth: str, *, writer: str = "engine") -> bool:
        """Flush dirty rows as a new immutable manifest-log/ segment on IA.

        Snapshot-and-clear under the lock: rows re-marked while the upload
        is in flight stay dirty for the next flush. On failure the snapshot
        is merged back so no observation is ever dropped (at-least-once;
        compaction upserts are idempotent). Returns True when there was
        nothing to flush or the upload succeeded.
        """
        from djen_backup.archive import put_ia_bytes
        from djen_backup.segments import SEGMENT_DIR, default_run_id, segment_name

        async with self._lock:
            if not self._dirty:
                return True
            pending = self._dirty
            self._dirty = set()
            content = self._serialize_rows(pending).encode("utf-8")

        if self._run_id is None:
            self._run_id = default_run_id()
        name = segment_name(writer, self._run_id)
        url = _IA_S3_URL.format(f"{SEGMENT_DIR}/{name}")
        headers = {
            "Authorization": auth,
            "Content-Type": "text/csv",
            "x-amz-auto-make-bucket": "1",
            "x-archive-meta-mediatype": "data",
        }
        ok = False
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await put_ia_bytes(client, url, content, headers)
                if resp.status_code < 400:
                    ok = True
                    log.info("manifest_segment_uploaded", name=name, rows=len(pending))
                else:
                    log.warning("manifest_segment_upload_failed", status=resp.status_code)
        except (httpx.HTTPError, httpx.RequestError) as exc:
            log.warning("manifest_segment_upload_error", error=str(exc))

        if not ok:
            async with self._lock:
                self._dirty |= pending
        return ok

    # ── Event merge (parquet base + segments, last-write-wins) ──────

    def apply_event(
        self,
        tribunal: str,
        d: date,
        *,
        ia_status: str = "",
        djen_status: str = "",
        djen_raw: str = "",
        updated_at: str = "",
    ) -> None:
        """Apply one upsert event with field-level last-write-wins semantics.

        Empty fields mean "no change" (plan §4.1 — partial events allowed).
        ``ia_status='uploaded'`` is monotonic: a verified archive fact is
        applied regardless of timestamps and never reverted. DJEN fields only
        apply when the event is not older than the entry (ISO timestamps
        compare lexicographically; an entry without ``updated_at`` loses).
        Never dirties the entry — loaded state is not a new observation.
        """
        tribunal = tribunal.upper()
        djen_status, djen_raw = self._normalize_event(djen_status, djen_raw)

        k = self._key(tribunal, d)
        entry = self._entries.get(k)
        if entry is None:
            entry = ManifestEntry(
                tribunal=tribunal,
                date=d,
                ia_status=ia_status,
                djen_status=djen_status,
                djen_raw=djen_raw,
                updated_at=updated_at,
            )
            self._entries[k] = entry
            return

        newer = updated_at >= (entry.updated_at or "")
        if ia_status == "uploaded" and entry.ia_status != "uploaded":
            entry.ia_status = "uploaded"
            entry.updated_at = max(entry.updated_at, updated_at)
        if (djen_status or djen_raw) and newer:
            entry.djen_status = djen_status
            entry.djen_raw = djen_raw
            entry.updated_at = max(entry.updated_at, updated_at)

    @staticmethod
    def _normalize_event(djen_status: str, djen_raw: str) -> tuple[str, str]:
        """Normalize event vocabulary for the engine's in-memory model.

        - ``confirmed`` is a parquet/drain-only refinement of ``available``;
          the engine's flows (``entries_needing_upload``, ``_categorize``)
          only know ``available``.
        - An ``absent`` verdict with a bare 200 raw contradicts itself
          (``interpret_djen_raw('200')`` derives available). Rewrite the raw
          to the ``no_publications`` sentinel so the row re-derives to
          absent from the raw alone (plan §5 Fase 1 self-consistency).
        """
        if djen_status == "confirmed":
            djen_status = "available"
        if djen_status == "absent" and (djen_raw == "200" or djen_raw.startswith("200:")):
            djen_raw = "no_publications"
        return djen_status, djen_raw

    def apply_segment_csv(self, text: str) -> int:
        """Apply a manifest-log segment (6-col event CSV). Returns rows applied."""
        applied = 0
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("tribunal"):
                continue
            parts = line.split(",")
            if len(parts) < 6:
                continue
            try:
                d = date.fromisoformat(parts[1])
            except ValueError:
                continue
            self.apply_event(
                parts[0],
                d,
                ia_status=parts[2],
                djen_status=parts[3],
                djen_raw=parts[4],
                updated_at=parts[5],
            )
            applied += 1
        if applied:
            self._invalidate_caches()
        return applied

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
    #
    # Phase 3 (plan §5): the canonical CSV is retired entirely. The only
    # read path is parquet base + un-compacted manifest-log segments; there
    # is no CSV fallback. A transient parquet outage is handled with a
    # bounded retry, then graceful degradation (return 0, engine keeps
    # running with whatever local disk cache it already has).

    _LOAD_FROM_IA_RETRIES = 3
    _LOAD_FROM_IA_RETRY_BACKOFF_S = 2.0

    async def load_from_ia(self) -> int:
        """Load state from IA: parquet base + un-compacted manifest-log segments.

        Phase 3 read path (plan §5): the compacted ``sync-manifest.parquet``
        is the sole source of truth (it is the verified-correct
        materialization — see CLAUDE.md Correctness), and any segments the
        compactor has not yet absorbed are replayed on top, field-level
        last-write-wins by ``updated_at``. Retries a bounded number of times
        on transient failure; never falls back to the retired CSV.
        """
        last_exc: Exception | None = None
        for attempt in range(1, self._LOAD_FROM_IA_RETRIES + 1):
            try:
                return await self._load_from_parquet_and_segments()
            except (
                httpx.HTTPError,
                httpx.RequestError,
                OSError,
                RuntimeError,
                ValueError,
            ) as exc:
                last_exc = exc
                log.warning(
                    "manifest_parquet_load_attempt_failed",
                    attempt=attempt,
                    max_attempts=self._LOAD_FROM_IA_RETRIES,
                    error=str(exc),
                )
                if attempt < self._LOAD_FROM_IA_RETRIES:
                    await asyncio.sleep(self._LOAD_FROM_IA_RETRY_BACKOFF_S * attempt)
        log.error("manifest_parquet_load_failed", error=str(last_exc))
        return 0

    async def _load_from_parquet_and_segments(self) -> int:
        import tempfile

        before = len(self._entries)
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            resp = await client.get(_IA_DOWNLOAD_URL.format(IA_PARQUET_FILENAME))
            _raise_unless_ok(resp.status_code, IA_PARQUET_FILENAME)

            with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name
            try:
                rows = await asyncio.to_thread(_read_parquet_rows, tmp_path)
            finally:
                await anyio.Path(tmp_path).unlink(missing_ok=True)

            for tribunal, d, ia_status, djen_status, djen_raw, updated_at in rows:
                self.apply_event(
                    tribunal,
                    d,
                    ia_status=ia_status or "",
                    djen_status=djen_status or "",
                    djen_raw=djen_raw or "",
                    updated_at=updated_at or "",
                )
            log.info("manifest_loaded_from_parquet", rows=len(rows))

            segment_names = await self._list_pending_segments(client)
            applied = 0
            for name in sorted(segment_names):
                seg_resp = await client.get(_IA_DOWNLOAD_URL.format(name))
                if seg_resp.status_code != 200:
                    log.warning("segment_download_failed", name=name, status=seg_resp.status_code)
                    continue
                applied += self.apply_segment_csv(seg_resp.text)
            if segment_names:
                log.info("manifest_segments_replayed", segments=len(segment_names), events=applied)

        self._invalidate_caches()
        return len(self._entries) - before

    @staticmethod
    async def _list_pending_segments(client: httpx.AsyncClient) -> list[str]:
        """List manifest-log/ segments not yet compacted (plan §4.3)."""
        from djen_backup.segments import SEGMENT_COMPACTED_DIR, SEGMENT_DIR

        resp = await client.get(_IA_FILES_METADATA_URL)
        if resp.status_code != 200:
            return []
        try:
            files = resp.json().get("result", [])
        except ValueError:
            return []
        names: list[str] = []
        for f in files:
            name = f.get("name", "") if isinstance(f, dict) else ""
            if (
                name.startswith(f"{SEGMENT_DIR}/")
                and not name.startswith(f"{SEGMENT_COMPACTED_DIR}/")
                and name.endswith(".csv")
            ):
                names.append(name)
        return names

    async def upload_summary_to_ia(self, auth: str) -> bool:
        """Upload compact JSON summary for the webapp."""
        import json

        from djen_backup.archive import put_ia_bytes

        url = _IA_S3_URL.format("manifest-summary.json")
        content = json.dumps(self.to_summary(), indent=2).encode("utf-8")
        headers = {
            "Authorization": auth,
            "Content-Type": "application/json",
            "x-amz-auto-make-bucket": "1",
            "x-archive-meta-mediatype": "data",
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await put_ia_bytes(client, url, content, headers)
                if resp.status_code < 400:
                    log.info("manifest_summary_uploaded_to_ia", size=len(content))
                    return True
                log.warning("manifest_summary_upload_failed", status=resp.status_code)
        except (httpx.HTTPError, httpx.RequestError) as exc:
            log.warning("manifest_summary_upload_error", error=str(exc))
        return False
