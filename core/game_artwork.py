"""Game cover-artwork resolution — real images only, from Steam's public
store APIs. No API key is required (and none is supported).

Why not a fixed URL pattern: newer Steam titles 404 on the legacy
``/steam/apps/<appid>/header.jpg`` path — they live under hashed
``store_item_assets`` URLs that only the appdetails API reveals. So the
pipeline tries, in order, first success wins:

  1. A previously cached image on disk (served instantly, no network).
  2. The legacy CDN URL for the record's appid (fast path for older titles).
  3. ``store.steampowered.com/api/appdetails`` -> ``data.header_image``
     for the record's appid (the authoritative current asset URL).
  4. A local icon the launcher itself ships (``icon_path``: Steam's .ico
     cache, a registry DisplayIcon) — instant, offline, and by construction
     this exact game; the guaranteed floor so a card is never empty even
     when the store APIs are unreachable.
  5. No appid? ``storesearch`` resolves the game's name to an appid — but
     only on an exact normalized-name match (or a >=0.92 similarity), so a
     cover can never be attached to the wrong game — then step 3.
  6. Last resort: the game's OWN embedded icon, extracted from its exe on
     Windows (System.Drawing — no extra Python dependency). Roblox,
     emulators and other non-Steam titles resolve here, so a card is only
     ever empty when its executable carries no icon either.

Failures are negatively cached for a day: an unavailable cover answers
"not found" quickly instead of re-hitting the network on every request.
The frontend swaps to its designed fallback tile on 404 — never a
broken-image icon.

Every response is validated (image content-type AND magic bytes AND a
sane size) so an HTML error page can never be cached as "artwork".
"""

import base64
import difflib
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

from .config import CONFIG
from .logger import get_logger

logger = get_logger("game_artwork")

# Public Steam store endpoints — no key, anonymous access.
_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"
_DETAILS_URL = "https://store.steampowered.com/api/appdetails"
_LEGACY_CDN = "https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg"

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Optinix/1.0 (+local artwork fetch)"

_POSITIVE_TTL_S = 30 * 24 * 3600   # covers rarely change; refresh monthly
_NEGATIVE_TTL_S = 24 * 3600        # retry an unresolved game once a day
_HTTP_TIMEOUT_S = 6.0
_MAX_IMAGE_BYTES = 6 * 1024 * 1024
_MIN_IMAGE_BYTES = 1_024
# Local icon files are trusted (they live on this machine, next to the
# install); only a size ceiling and real magic bytes still apply.
_LOCAL_MIN_IMAGE_BYTES = 64
# Store name vs library name must be essentially the same game.
_MATCH_FLOOR = 0.92

_IMAGE_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG", "image/png"),
    (b"GIF8", "image/gif"),
    (b"\x00\x00\x01\x00", "image/x-icon"),  # Windows .ico (launcher icons)
)
_WEBP_MAGIC = (b"RIFF", 4, 8, b"WEBP")  # offset-based: RIFF????WEBP


def _sniff_image_mime(head: bytes) -> Optional[str]:
    """Content type the bytes actually are, or None if not an image."""
    for magic, mime in _IMAGE_MAGIC:
        if head.startswith(magic):
            return mime
    if len(head) >= 12 and head[:4] == _WEBP_MAGIC[0] and head[8:12] == _WEBP_MAGIC[3]:
        return "image/webp"
    return None


def _exe_icon_png(exe: str) -> bytes:
    """The exe's own embedded icon as PNG bytes (Windows only).

    System.Drawing does the format work (HICON -> PNG); the path travels in
    an environment variable so nothing is interpolated into the command
    line. Returns b'' on any failure — the caller negative-caches.
    """
    if os.name != "nt" or not exe or not os.path.isfile(exe):
        return b""
    script = (
        "Add-Type -AssemblyName System.Drawing -ErrorAction SilentlyContinue; "
        "try { $i=[System.Drawing.Icon]::ExtractAssociatedIcon($env:OPTINIX_ICON_EXE); "
        "if (-not $i) { exit 1 }; $b=$i.ToBitmap(); "
        "$ms=New-Object System.IO.MemoryStream; "
        "$b.Save($ms,[System.Drawing.Imaging.ImageFormat]::Png); "
        "[Convert]::ToBase64String($ms.ToArray()) } catch { exit 1 }"
    )
    env = dict(os.environ, OPTINIX_ICON_EXE=exe)
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, timeout=10, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0 or not proc.stdout:
            return b""
        return base64.b64decode(proc.stdout, validate=False)[:_MAX_IMAGE_BYTES]
    except Exception as e:
        logger.debug(f"exe icon extraction failed for {exe!r}: {e}")
        return b""


def _fetch(url: str, timeout: float = _HTTP_TIMEOUT_S) -> Tuple[int, Dict[str, str], bytes]:
    """GET one URL: (status, headers, body). Raises on network failure.

    Kept as a module function so tests can stub the network at one seam.
    """
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https hosts
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read(_MAX_IMAGE_BYTES + 1)
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, dict(e.headers.items()) if e.headers else {}, body


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", name.casefold())).strip()


def _name_matches(library_name: str, store_name: str) -> bool:
    """True only when the store result is clearly the same game."""
    a, b = _normalize(library_name), _normalize(store_name)
    if not a or not b:
        return False
    if a == b:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= _MATCH_FLOOR


class ArtworkStore:
    """Disk-backed artwork cache with negative caching.

    Layout inside ``cache_dir``: ``<sha1>.img`` (image bytes) alongside
    ``<sha1>.json`` (metadata), or ``<sha1>.none.json`` for a negative.
    The key is the game's stable id plus its name, so a rename re-resolves.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or os.path.join(CONFIG.base_dir, "data", "artwork_cache")
        self._lock = threading.Lock()

    # -- cache helpers ----------------------------------------------------
    def _key(self, game: Dict[str, Any]) -> str:
        raw = f"{game.get('id', '')}|{game.get('name', '')}"
        return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()

    def _img_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.img")

    def _meta_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def _read_meta(self, key: str) -> Dict[str, Any]:
        try:
            with open(self._meta_path(key), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_meta(self, key: str, meta: Dict[str, Any]) -> None:
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            tmp = self._meta_path(key) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(meta, f)
            os.replace(tmp, self._meta_path(key))
        except Exception as e:  # cache write failures must never break serving
            logger.debug(f"artwork meta write failed: {e}")

    def _cached_image(self, key: str) -> Optional[Tuple[bytes, str]]:
        meta = self._read_meta(key)
        if not meta.get("found") or not meta.get("file"):
            return None
        if time.time() - meta.get("ts", 0) > _POSITIVE_TTL_S:
            return None
        try:
            with open(self._img_path(key), "rb") as f:
                body = f.read(_MAX_IMAGE_BYTES + 1)
        except OSError:
            return None
        mime = _sniff_image_mime(body[:16]) or meta.get("mime") or "image/jpeg"
        return body, mime

    def _negative_fresh(self, key: str) -> bool:
        meta = self._read_meta(key)
        if meta.get("found"):
            return False
        return time.time() - meta.get("ts", 0) < _NEGATIVE_TTL_S

    def _store_positive(self, key: str, body: bytes, mime: str, source: str, appid: Optional[int]) -> None:
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self._img_path(key), "wb") as f:
                f.write(body)
            self._write_meta(key, {
                "found": True, "file": os.path.basename(self._img_path(key)),
                "mime": mime, "ts": time.time(), "source": source, "appid": appid,
            })
        except OSError as e:
            logger.debug(f"artwork image write failed: {e}")

    def _store_negative(self, key: str, reason: str) -> None:
        self._write_meta(key, {"found": False, "ts": time.time(), "reason": reason[:200]})

    # -- resolution steps -------------------------------------------------
    @staticmethod
    def _valid_image(body: bytes, headers: Dict[str, str]) -> Optional[str]:
        ctype = (headers.get("content-type") or "").split(";")[0].strip().lower()
        if not _MIN_IMAGE_BYTES <= len(body) <= _MAX_IMAGE_BYTES:
            return None
        sniffed = _sniff_image_mime(body[:16])
        if not sniffed:
            return None  # HTML/JSON error body pretending to be an image
        # A mismatched declared type is suspicious but the bytes decide.
        if ctype.startswith("text/") and not sniffed:
            return None
        return sniffed

    def _download(self, url: str) -> Optional[Tuple[bytes, str]]:
        try:
            status, headers, body = _fetch(url)
        except Exception as e:  # network down / DNS / timeout
            logger.debug(f"artwork fetch failed {url}: {e}")
            return None
        if status != 200:
            return None
        mime = self._valid_image(body, headers)
        if not mime:
            return None
        return body, mime

    @staticmethod
    def _resolve_appid_by_name(name: str) -> Optional[int]:
        """storesearch -> appid, only for a convincing name match."""
        url = f"{_SEARCH_URL}?{urllib.parse.urlencode({'term': name, 'cc': 'US', 'l': 'en'})}"
        try:
            status, _, body = _fetch(url)
            if status != 200:
                return None
            data = json.loads(body.decode("utf-8", "replace"))
        except Exception as e:
            logger.debug(f"storesearch failed for {name!r}: {e}")
            return None
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return None
        for item in items:
            if not isinstance(item, dict) or item.get("type") != "app":
                continue  # never match DLC/subs/soundtracks as the game
            if _name_matches(name, str(item.get("name", ""))):
                try:
                    return int(item["id"])
                except (KeyError, TypeError, ValueError):
                    continue
        return None

    @staticmethod
    def _header_image_for(appid: int) -> Optional[str]:
        """appdetails -> the game's current (possibly hashed) header image URL."""
        url = f"{_DETAILS_URL}?{urllib.parse.urlencode({'appids': str(appid), 'cc': 'US', 'l': 'en'})}"
        try:
            status, _, body = _fetch(url)
            if status != 200:
                return None
            data = json.loads(body.decode("utf-8", "replace"))
        except Exception as e:
            logger.debug(f"appdetails failed for {appid}: {e}")
            return None
        entry = data.get(str(appid)) if isinstance(data, dict) else None
        if not isinstance(entry, dict) or not entry.get("success"):
            return None
        header = (entry.get("data") or {}).get("header_image")
        if isinstance(header, str) and header.startswith("https://"):
            return header
        return None

    # -- public -----------------------------------------------------------
    def resolve(self, game: Dict[str, Any]) -> Optional[Tuple[bytes, str]]:
        """Image bytes + mime for this game, or None (frontend fallback)."""
        key = self._key(game)
        with self._lock:
            hit = self._cached_image(key)
            if hit:
                return hit
            if self._negative_fresh(key):
                return None

            appid: Optional[int] = None
            raw_appid = game.get("appid")
            if raw_appid:
                try:
                    appid = int(raw_appid)
                except (TypeError, ValueError):
                    appid = None
            name = str(game.get("name") or "").strip()

            result: Optional[Tuple[bytes, str]] = None
            source = "none"

            # Local launcher icon (Steam's cached .ico, a registry
            # DisplayIcon): a guaranteed offline answer for this exact game.
            # Network covers win when they respond (a wide cover beats an
            # icon); the local file is the floor so no card is ever empty.
            local: Optional[Tuple[bytes, str]] = None
            icon_path = str(game.get("icon_path") or "")
            exe = str(game.get("exe_path") or "")
            if icon_path and os.path.isfile(icon_path):
                try:
                    with open(icon_path, "rb") as fh:
                        raw = fh.read(_MAX_IMAGE_BYTES + 1)
                except OSError:
                    raw = b""
                mime = _sniff_image_mime(raw[:16])
                if mime and _LOCAL_MIN_IMAGE_BYTES <= len(raw) <= _MAX_IMAGE_BYTES:
                    local = (raw, mime)

            if appid:
                # Legacy path first: one cheap request for older titles.
                result = self._download(_LEGACY_CDN.format(appid=appid))
                if result:
                    source = "steam-legacy"
                else:
                    header = self._header_image_for(appid)
                    if header:
                        result = self._download(header)
                        if result:
                            source = "steam-appdetails"

            if not result and local:
                # Network down, or the cover APIs missed for this appid —
                # the launcher's own icon still answers.
                result, source = local, "local-icon"

            if not result and name and not appid:
                # No appid on the record (non-Steam launcher, manual import):
                # resolve by name, but only an exact-similar store hit counts.
                resolved = self._resolve_appid_by_name(name)
                if resolved:
                    header = self._header_image_for(resolved)
                    if header:
                        result = self._download(header)
                        if result:
                            appid = resolved
                            source = "steam-name-lookup"

            if not result and exe:
                # Last resort: the game's own embedded icon (Windows). A
                # real 32x32 logo beats an empty tile — Roblox, emulators
                # and other non-Steam titles land here.
                raw = _exe_icon_png(exe)
                mime = _sniff_image_mime(raw[:16])
                if mime and _LOCAL_MIN_IMAGE_BYTES <= len(raw) <= _MAX_IMAGE_BYTES:
                    result, source = (raw, mime), "exe-icon"

            if result:
                self._store_positive(key, result[0], result[1], source, appid)
                logger.debug(f"artwork resolved for {name!r} via {source}")
                return result

            self._store_negative(key, "no valid artwork from any source")
            return None


# Process-wide store (the app writes data/ already; tests build their own).
STORE = ArtworkStore()
