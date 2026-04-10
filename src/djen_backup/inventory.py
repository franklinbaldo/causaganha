from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import structlog


log = structlog.get_logger()

IA_STATE_ITEM = "causaganha-dashboard"
IA_ZIP_INVENTORY_FILENAME = "zip-inventory.txt"
ZIP_INVENTORY_FILE = Path("data/zip-inventory.txt")

_IA_DOWNLOAD_URL = f"https://archive.org/download/{IA_STATE_ITEM}/{{}}"
_IA_S3_URL = f"https://s3.us.archive.org/{IA_STATE_ITEM}/{{}}"


async def download_text_from_ia(filename: str) -> str | None:
    """Download a text file from IA. Returns content string or None."""
    import httpx

    url = _IA_DOWNLOAD_URL.format(filename)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                log.info("text_downloaded_from_ia", filename=filename, size=len(resp.text))
                return resp.text
            log.info("text_not_found_on_ia", filename=filename, status=resp.status_code)
    except Exception as exc:
        log.warning("text_download_failed", filename=filename, error=str(exc))
    return None


async def upload_text_to_ia(filename: str, content: str, auth: str) -> bool:
    """Upload a text file to IA. Returns True on success."""
    import httpx

    url = _IA_S3_URL.format(filename)
    headers = {
        "Authorization": auth,
        "Content-Type": "text/plain",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.put(url, content=content.encode("utf-8"), headers=headers)
            if resp.status_code < 400:
                log.info("text_uploaded_to_ia", filename=filename)
                return True
            log.warning("text_upload_failed", filename=filename, status=resp.status_code)
    except Exception as exc:
        log.warning("text_upload_error", filename=filename, error=str(exc))
    return False


class ZipInventory:
    """CSV-based inventory of all known ZIPs on Internet Archive.

    Format (one line per entry, sorted by timestamp):
        TIMESTAMP,TRIBUNAL,DATE,STATUS,URL

    STATUS is ``uploaded`` or ``absent``.
    URL is the IA download URL for uploaded ZIPs, empty for absents.

    Lookup is O(1) via a ``{TRIBUNAL/DATE}`` keyed dict.
    """

    HEADER = "timestamp,tribunal,date,status,url"

    def __init__(self) -> None:
        # Key: "TRIBUNAL/YYYY-MM-DD" → (status, url, timestamp)
        self._entries: dict[str, tuple[str, str, str]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(tribunal: str, d: date) -> str:
        return f"{tribunal.upper()}/{d.isoformat()}"

    @staticmethod
    def _url(tribunal: str, d: date) -> str:
        item_id = f"djen-{tribunal.lower()}-{d.year}"
        filename = f"djen-{d.isoformat()}-{tribunal.upper()}.zip"
        return f"https://archive.org/download/{item_id}/{filename}"

    def has(self, tribunal: str, d: date) -> bool:
        """Check if date is known (either uploaded or absent)."""
        return self._key(tribunal, d) in self._entries

    def get_status(self, tribunal: str, d: date) -> str | None:
        """Return status (uploaded/absent/staged) or None if unknown."""
        entry = self._entries.get(self._key(tribunal, d))
        return entry[0] if entry else None

    async def add(self, tribunal: str, d: date) -> None:
        """Mark a date as uploaded (ZIP exists on IA)."""
        async with self._lock:
            k = self._key(tribunal, d)
            self._entries[k] = (
                "uploaded",
                self._url(tribunal, d),
                datetime.now(UTC).isoformat(timespec="seconds"),
            )

    async def add_staged(self, tribunal: str, d: date) -> None:
        """Mark a date as staged (ZIP exists locally in staging)."""
        async with self._lock:
            k = self._key(tribunal, d)
            self._entries[k] = (
                "staged",
                "",
                datetime.now(UTC).isoformat(timespec="seconds"),
            )

    async def add_absent(self, tribunal: str, d: date) -> None:
        """Mark a date as confirmed absent (no journal published)."""
        async with self._lock:
            k = self._key(tribunal, d)
            if k not in self._entries:
                self._entries[k] = (
                    "absent",
                    "",
                    datetime.now(UTC).isoformat(timespec="seconds"),
                )

    async def add_many(self, tribunal: str, dates: set[date]) -> None:
        async with self._lock:
            for d in dates:
                k = self._key(tribunal, d)
                if k not in self._entries:
                    self._entries[k] = (
                        "uploaded",
                        self._url(tribunal, d),
                        datetime.now(UTC).isoformat(timespec="seconds"),
                    )

    def __len__(self) -> int:
        """Return number of inventory entries."""
        return len(self._entries)

    def count_staged(self) -> int:
        """Return total number of files currently in staging."""
        return sum(1 for status, _, _ in self._entries.values() if status == "staged")

    def get_staged_by_item(self) -> dict[str, list[date]]:
        """Return a mapping of item_id -> list of dates that are staged."""
        items: dict[str, list[date]] = {}
        for k, (status, _, _) in self._entries.items():
            if status == "staged":
                tribunal, date_str = k.split("/", 1)
                d = date.fromisoformat(date_str)
                item_id = f"djen-{tribunal.lower()}-{d.year}"
                if item_id not in items:
                    items[item_id] = []
                items[item_id].append(d)
        return items

    def load_from_csv(self, text: str) -> int:
        """Load from CSV text. Returns count added."""
        before = len(self._entries)
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("timestamp"):
                continue
            parts = line.split(",", 4)
            if len(parts) < 4:
                continue
            ts, tribunal, date_str, status = parts[0], parts[1], parts[2], parts[3]
            url = parts[4] if len(parts) > 4 else ""
            k = f"{tribunal.upper()}/{date_str}"
            if k not in self._entries:
                self._entries[k] = (status, url, ts)
        return len(self._entries) - before

    def to_csv(self) -> str:
        """Serialize to CSV sorted by timestamp."""
        lines = [self.HEADER]
        rows = []
        for k, (status, url, ts) in self._entries.items():
            tribunal, date_str = k.split("/", 1)
            rows.append((ts, tribunal, date_str, status, url))
        rows.sort()  # Sorts by timestamp first
        for ts, tribunal, date_str, status, url in rows:
            lines.append(f"{ts},{tribunal},{date_str},{status},{url}")
        return "\n".join(lines) + "\n"

    async def load_from_ia(self) -> int:
        """Download inventory from Internet Archive. Returns count loaded."""
        text = await download_text_from_ia(IA_ZIP_INVENTORY_FILENAME)
        if text:
            return self.load_from_csv(text)
        return 0

    async def upload_to_ia(self, auth: str) -> bool:
        """Merge-then-upload: re-download remote inventory, merge with local, upload.

        This prevents race conditions when multiple runners update concurrently.
        Since entries are keyed by TRIBUNAL/DATE, the merge is idempotent.
        """
        remote_text = await download_text_from_ia(IA_ZIP_INVENTORY_FILENAME)
        if remote_text:
            self.load_from_csv(remote_text)
        return await upload_text_to_ia(IA_ZIP_INVENTORY_FILENAME, self.to_csv(), auth)

    def load_from_disk(self, path: Path = ZIP_INVENTORY_FILE) -> int:
        """Load from local disk as fallback. Returns count loaded."""
        if not path.exists():
            return 0
        return self.load_from_csv(path.read_text(encoding="utf-8"))

    def save_to_disk(self, path: Path = ZIP_INVENTORY_FILE) -> None:
        """Persist to local disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_csv(), encoding="utf-8")

    async def load_from_snapshot(self) -> int:
        """Seed from ia-snapshot.json (zero network)."""
        snapshot_path = Path("dashboard/public/ia-snapshot.json")
        if not snapshot_path.exists():
            return 0
        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0
        before = len(self._entries)
        for item_data in snapshot.get("items", {}).values():
            tribunal = item_data.get("tribunal", "")
            for date_str in item_data.get("dates", []):
                try:
                    d = date.fromisoformat(date_str)
                except ValueError:
                    continue
                await self.add(tribunal, d)
        return len(self._entries) - before

    def gaps_for_year(
        self,
        tribunal: str,
        year: int,
        upper: date,
        lower: date,
    ) -> list[date]:
        """Return days in the year that are NOT in inventory."""
        start = max(date(year, 1, 1), lower)
        end = min(date(year, 12, 31), upper)
        missing = []
        current = start
        t_upper = tribunal.upper()
        while current <= end:
            if f"{t_upper}/{current.isoformat()}" not in self._entries:
                missing.append(current)
            current += timedelta(days=1)
        return missing

    def is_year_complete(
        self,
        tribunal: str,
        year: int,
        upper: date,
        lower: date,
    ) -> bool:
        """Check if all days for this tribunal/year are already in inventory."""
        start = max(date(year, 1, 1), lower)
        end = min(date(year, 12, 31), upper)

        # If the start is after the end, this year isn't even in our range
        if start > end:
            return True

        t_upper = tribunal.upper()
        current = start
        while current <= end:
            if f"{t_upper}/{current.isoformat()}" not in self._entries:
                return False
            current += timedelta(days=1)
        return True
