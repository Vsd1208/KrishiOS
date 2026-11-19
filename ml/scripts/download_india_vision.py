"""Download a size-limited sample of Indian field crop-disease photos from Mendeley Data.

Archives are read in place with HTTP range requests, so only the chosen photos are transferred.
Every byte received counts against ``HARD_LIMIT`` (the project owner's 5 GB limit), including
archive indexes and retries, and the total is kept in ``ledger.json`` across runs.

Archive contents are treated as untrusted: member paths are never used as file paths, only
JPEG/PNG photos that Pillow can decode are kept, and each is saved under its content hash.

Usage (from ml/)::

    python -I scripts/download_india_vision.py inspect
    python -I scripts/download_india_vision.py download
"""

from __future__ import annotations

import hashlib
import http.client
import io
import json
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "vision" / "india"
LEDGER = ROOT / "ledger.json"
MANIFEST = ROOT / "manifest.jsonl"
API = "https://data.mendeley.com/api/datasets"
HEADERS = {"User-Agent": "dataset-downloader/1.0"}
HARD_LIMIT = 5_000_000_000
STOP_AT = 4_800_000_000  # keeps a margin below the limit
PHOTO_TYPES = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png"}
MAX_PIXELS = 80_000_000
MAX_PHOTO_BYTES = 64_000_000
SEED = "krishios-india-v1"
WORKERS = 3  # kept low: the storage link degrades under sustained parallel requests
PIECE = 256_000  # starting piece size; adapts between MIN_PIECE and MAX_PIECE
MIN_PIECE, MAX_PIECE = 128_000, 1_024_000
RESTARTS = 200
LEAF = "276b9709"  # MH-SoyaHealthVision's ground-level leaf folder (the other one is drone images)

# Archive name (or "<folder id>/<name>") -> crop and condition; a condition of None uses the
# photo's parent folder name. PLDD-UP mixes camera originals with small processed copies in every
# class, so one file-size band is applied to all of its classes.
SETS: dict[str, dict] = {
    "potato_pldd_up": {
        "id": "3j4nfkvp2n", "version": 1, "per_class": 450, "bytes": (800_000, 2_500_000),
        "archives": {"EB.zip": ("potato", "early_blight"), "LB.zip": ("potato", "late_blight"),
                     "Healthy.zip": ("potato", "healthy")}},
    "chilli_krishna": {
        "id": "ymt8k9bjkn", "version": 3, "per_class": None,
        "archives": {"Chili Leaf Disease Original Dataset.zip": ("chilli", None)}},
    "tomato_bskkv": {
        "id": "rv3kxfv47y", "version": 1, "per_class": None, "archives": {},
        "whole": ["Real world data.7z"]},
    "soybean_mh": {
        "id": "hkbgh5s3b7", "version": 1, "per_class": 70,
        "archives": {f"{LEAF}/Healthy_Soyabean.zip": ("soybean", "healthy"),
                     f"{LEAF}/Soyabean_Rust.zip": ("soybean", "rust"),
                     f"{LEAF}/Soyabean_Mosaic.zip": ("soybean", "mosaic"),
                     f"{LEAF}/Soyabean_Frog_Leaf_Eye.zip": ("soybean", "frogeye_leaf_spot"),
                     f"{LEAF}/Soyabean_Spectoria_Brown_Spot.zip":
                         ("soybean", "septoria_brown_spot"),
                     f"{LEAF}/Caterpillar and Semilooper Pest Attack.zip":
                         ("soybean", "pest_damage")}},
    "wheat_iari": {
        "id": "th422bg4yd", "version": 1, "per_class": None,
        "archives": {"WheatLeafRust.zip": ("wheat", None)}},
}


class Budget:
    def __init__(self) -> None:
        self.used = json.loads(LEDGER.read_text())["bytes"] if LEDGER.exists() else 0
        self.last_saved = self.used
        self.reserved = 0
        self.lock = threading.RLock()

    def check(self, n: int) -> None:
        """Parallel requests each hold back their size, so together they cannot pass the stop."""
        with self.lock:
            if self.used + self.reserved + n > min(STOP_AT, HARD_LIMIT):
                self.save()
                raise SystemExit(f"stopping: {self.used / 1e9:.3f} GB used; limit is 5 GB")

    def reserve(self, n: int) -> None:
        with self.lock:
            self.check(n)
            self.reserved += n

    def release(self, n: int) -> None:
        with self.lock:
            self.reserved -= n

    def add(self, n: int) -> None:
        with self.lock:
            self.used += n
            if self.used - self.last_saved > 5_000_000:
                self.save()

    def save(self) -> None:
        with self.lock:
            ROOT.mkdir(parents=True, exist_ok=True)
            tmp = LEDGER.with_suffix(".tmp")
            tmp.write_text(json.dumps({"bytes": self.used}))
            tmp.replace(LEDGER)
            self.last_saved = self.used


def api_files(dataset: str, version: int) -> list[dict]:
    req = urllib.request.Request(f"{API}/{dataset}/files?version={version}",
                                 headers={**HEADERS, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


class RangeFile(io.RawIOBase):
    """A remote file read with range requests; every received byte is counted."""

    def __init__(self, url: str, size: int, budget: Budget) -> None:
        self.url, self.size, self.budget, self.pos = url, size, budget, 0
        self.target: urllib.parse.SplitResult | None = None  # storage URL after the redirect
        self.piece = PIECE
        self.streak = 0
        self.local = threading.local()  # one kept-alive connection per worker thread
        self.lock = threading.Lock()

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def fetch(self, start: int, n: int) -> bytes:
        """Pieces sized to what the link sustains: larger after a run of successes, smaller
        after a stall (on this link long transfers can stall while short ones finish)."""
        self.budget.check(n)
        out, pos, end = [], start, start + n
        while pos < end:
            size = min(self.piece, end - pos)
            out.append(self._piece(pos, size))
            pos += size
        return b"".join(out)

    def _resolve(self) -> None:
        """Follow the dataset link's redirect once and keep the storage URL it points to."""
        req = urllib.request.Request(self.url, headers={**HEADERS, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            self.budget.add(len(r.read()))
            self.target = urllib.parse.urlsplit(r.geturl())

    def _connection(self) -> http.client.HTTPSConnection:
        conn = getattr(self.local, "conn", None)
        if conn is None or getattr(self.local, "host", None) != self.target.netloc:
            conn = http.client.HTTPSConnection(self.target.netloc, timeout=30)
            self.local.conn, self.local.host = conn, self.target.netloc
        return conn

    def _drop_connection(self) -> None:
        conn = getattr(self.local, "conn", None)
        if conn is not None:
            conn.close()
        self.local.conn = None

    def _adapt(self, ok: bool) -> None:
        with self.lock:
            if ok:
                self.streak += 1
                if self.streak >= 4 and self.piece < MAX_PIECE:
                    self.piece, self.streak = min(MAX_PIECE, self.piece * 2), 0
            else:
                self.piece, self.streak = max(MIN_PIECE, self.piece // 2), 0

    def _piece(self, start: int, n: int) -> bytes:
        for attempt in range(1, 9):
            try:
                if self.target is None:
                    with self.lock:
                        if self.target is None:
                            self._resolve()
                path = self.target.path + (f"?{self.target.query}" if self.target.query else "")
                conn = self._connection()
                conn.request("GET", path, headers={**HEADERS, "Range":
                                                   f"bytes={start}-{start + n - 1}"})
                r = conn.getresponse()
                data = r.read()
                self.budget.add(len(data))
                if r.status in (301, 302, 307, 400, 401, 403):  # storage link expired
                    self.target = None
                    raise OSError(f"storage returned {r.status}")
                if r.status != 206 or len(data) != n:
                    raise OSError(f"range request returned {r.status}, {len(data)} bytes")
                self._adapt(True)
                return data
            except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
                if isinstance(exc, http.client.IncompleteRead):
                    self.budget.add(len(exc.partial))  # received bytes still count
                self._drop_connection()
                self._adapt(False)
                if attempt == 8:
                    raise
                time.sleep(min(60, 5 * attempt))
        raise AssertionError("unreachable")

    def readinto(self, b) -> int:
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        b[:n] = self.fetch(self.pos, n)
        self.pos += n
        return n


def open_archive(file: dict, budget: Budget) -> zipfile.ZipFile:
    c = file["content_details"]
    raw = RangeFile(c["download_url"], int(c["size"]), budget)
    zf = zipfile.ZipFile(io.BufferedReader(raw, buffer_size=16_384))
    zf.remote = raw  # type: ignore[attr-defined]
    return zf


def read_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes | None:
    """One photo in a single range request. Returns None if it is unusable."""
    if info.file_size > MAX_PHOTO_BYTES or info.compress_type not in {0, 8} or info.flag_bits & 1:
        return None
    name_len = len(info.orig_filename.encode("utf-8", "surrogateescape"))
    n = 30 + name_len + len(info.extra) + info.compress_size + 512
    n = min(n, zf.remote.size - info.header_offset)  # type: ignore[attr-defined]
    budget = zf.remote.budget  # type: ignore[attr-defined]
    budget.reserve(n)
    try:
        block = zf.remote.fetch(info.header_offset, n)  # type: ignore[attr-defined]
    finally:
        budget.release(n)
    if block[:4] != b"PK\x03\x04":
        return None
    name, extra = struct.unpack("<HH", block[26:30])
    start = 30 + name + extra
    data = block[start:start + info.compress_size]
    if len(data) != info.compress_size:
        data += zf.remote.fetch(  # type: ignore[attr-defined]
            info.header_offset + len(block), info.compress_size - len(data))
    if info.compress_type == 8:
        inflater = zlib.decompressobj(-15)
        data = inflater.decompress(data, MAX_PHOTO_BYTES + 1)
    if len(data) != info.file_size or zlib.crc32(data) != info.CRC:
        return None
    return data


def download_whole(file: dict, folder: Path, budget: Budget) -> None:
    c = file["content_details"]
    size, path = int(c["size"]), folder / "archive.7z"
    if path.exists() and path.stat().st_size == size:
        return
    part = folder / "archive.part"
    raw = RangeFile(c["download_url"], size, budget)
    budget.check(size - (part.stat().st_size if part.exists() else 0))
    with part.open("ab") as out:
        pos = out.tell()
        while pos < size:
            n = min(4_000_000, size - pos)
            out.write(raw.fetch(pos, n))
            out.flush()
            pos += n
            budget.save()
    if hashlib.sha256(part.read_bytes()).hexdigest() != c["sha256_hash"]:
        part.unlink()
        raise SystemExit("archive checksum mismatch: partial file removed")
    part.replace(path)


def photos(zf: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    return [i for i in zf.infolist() if not i.is_dir()
            and PurePosixPath(i.filename).suffix.lower() in PHOTO_TYPES
            and "__MACOSX" not in i.filename]


def inspect(budget: Budget) -> None:
    from PIL import Image

    for name, spec in SETS.items():
        for f in api_files(spec["id"], spec["version"]):
            label = f"{name} | {str(f.get('folder_id'))[:8]} | {f['filename']}"
            if not f["filename"].lower().endswith(".zip"):
                continue
            if name == "chilli_krishna" and "Original" not in f["filename"]:
                continue
            if name == "wheat_iari" and "Rust" not in f["filename"]:
                continue
            with open_archive(f, budget) as zf:
                items = photos(zf)
                dirs: Counter = Counter()
                sizes: Counter = Counter()
                for i in items:
                    d = "/".join(PurePosixPath(i.filename).parts[:-1])[:60]
                    dirs[d] += 1
                    sizes[d] += i.compress_size
                print(f"{label}: {len(items)} photos, "
                      f"{sum(i.compress_size for i in items) / 1e6:.0f} MB", flush=True)
                for d, n in dirs.most_common(14):
                    print(f"    {n:5d}  {sizes[d] / 1e6:7.1f} MB  {d}", flush=True)
                if items:
                    with zf.open(items[len(items) // 2]) as fh, Image.open(
                            io.BytesIO(fh.read())) as im:
                        print(f"    sample size {im.size}", flush=True)
    budget.save()
    print(f"bytes used so far: {budget.used / 1e6:.1f} MB")


def rank(key: str) -> str:
    return hashlib.sha256(f"{SEED}:{key}".encode()).hexdigest()


def save_photo(data: bytes, suffix: str, folder: Path) -> tuple[str, list[int]] | None:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.format not in {"JPEG", "PNG"}:
                return None
            size = list(im.size)
            im.load()
    except Exception:  # corrupt or hostile file: skip it
        return None
    digest = hashlib.sha256(data).hexdigest()
    path = folder / f"{digest}{suffix}"
    if not path.exists():
        tmp = path.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(path)
    return digest, size


def download(budget: Budget) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    done, have = set(), Counter()
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["set"], r["archive"], r["member"]))
            have[(r["set"], r["crop"], r["raw_class"])] += 1
    with MANIFEST.open("a", encoding="utf-8") as out:
        for name, spec in SETS.items():
            folder = ROOT / name
            folder.mkdir(exist_ok=True)
            low, high = spec.get("bytes", (0, MAX_PHOTO_BYTES))
            for f in api_files(spec["id"], spec["version"]):
                if f["filename"] in spec.get("whole", ()):
                    download_whole(f, folder, budget)
                    print(f"finished {name} / {f['filename']}: {budget.used / 1e9:.3f} GB",
                          flush=True)
                    continue
                key = f"{str(f.get('folder_id'))[:8]}/{f['filename']}"
                target = spec["archives"].get(key) or spec["archives"].get(f["filename"])
                if target is None:
                    continue
                crop, fixed = target
                with open_archive(f, budget) as zf:
                    classes = defaultdict(list)
                    for i in photos(zf):
                        if not low <= i.compress_size <= high:
                            continue
                        parts = PurePosixPath(i.filename).parts
                        classes[fixed or (parts[-2] if len(parts) > 1 else "unknown")].append(i)
                    for raw_class, items in classes.items():
                        items.sort(key=lambda i: rank(f"{name}:{raw_class}:{i.filename}"))
                        count_key = (name, crop, raw_class)
                        todo = [i for i in items
                                if (name, f["filename"], i.filename) not in done]

                        def get_one(i: zipfile.ZipInfo, zf=zf, folder=folder):
                            suffix = PHOTO_TYPES[PurePosixPath(i.filename).suffix.lower()]
                            data = read_member(zf, i)
                            saved = save_photo(data, suffix, folder) if data else None
                            return i, suffix, saved

                        while todo:
                            need = (spec["per_class"] - have[count_key]
                                    if spec["per_class"] else len(todo))
                            if need <= 0:
                                break
                            batch, todo = todo[:min(need, WORKERS * 4)], todo[min(need,
                                                                                  WORKERS * 4):]
                            with ThreadPoolExecutor(WORKERS) as pool:
                                for i, suffix, saved in pool.map(get_one, batch):
                                    if saved is None:
                                        continue
                                    digest, size = saved
                                    out.write(json.dumps({
                                        "set": name, "archive": f["filename"],
                                        "member": i.filename, "crop": crop,
                                        "raw_class": raw_class, "sha256": digest,
                                        "file": f"{name}/{digest}{suffix}", "width": size[0],
                                        "height": size[1]}) + "\n")
                                    out.flush()
                                    done.add((name, f["filename"], i.filename))
                                    have[count_key] += 1
                                    if sum(have.values()) % 50 == 0:
                                        budget.save()
                                        print(f"{sum(have.values())} photos, "
                                              f"{budget.used / 1e9:.3f} GB", flush=True)
                print(f"finished {name} / {f['filename']}: {budget.used / 1e9:.3f} GB", flush=True)
    budget.save()
    print(json.dumps({f"{s}|{c}|{k}": n for (s, c, k), n in sorted(have.items())}, indent=1))
    print(f"total transferred: {budget.used / 1e9:.3f} GB")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in {"inspect", "download"}:
        raise SystemExit("usage: download_india_vision.py inspect|download")
    b = Budget()
    if mode == "inspect":
        inspect(b)
    else:
        for restart in range(1, RESTARTS + 1):
            try:
                download(b)
                break
            except Exception as exc:  # flaky network; only the type is logged (links are signed)
                b.save()
                print(f"restart {restart}: {type(exc).__name__}", flush=True)
                time.sleep(60)
        else:
            raise SystemExit("too many failures; run again to resume")
