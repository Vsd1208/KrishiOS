"""Phase 10c: load the vetted guides from ``fetch_knowledge_sources.py`` into the knowledge base.

Sends each file in ``data/raw/knowledge/manifest.json`` to the backend's document upload endpoint
with its title, publisher, URL, region and crops, so every retrieved passage carries a citation.
The backend skips exact duplicates (SHA-256), so the script can be run again.

Usage (from ml/, backend running)::

    python -I scripts/upload_knowledge_sources.py [--api http://127.0.0.1:8000/api/v1]
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "data" / "raw" / "knowledge"


def post_file(api: str, path: Path, metadata: dict) -> dict:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"metadata\"\r\n\r\n".encode()
        + json.dumps(metadata).encode() + b"\r\n",
        (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
         f"filename=\"{path.name}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        + path.read_bytes() + b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(f"{api}/documents/upload", data=b"".join(parts), method="POST",
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read())


def get(api: str, path: str) -> dict:
    with urllib.request.urlopen(f"{api}{path}", timeout=900) as resp:  # embedding blocks the server
        return json.loads(resp.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8000/api/v1")
    args = ap.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    for key, src in manifest.items():
        meta = {"title": src["title"], "document_type": "package_of_practices", "language": "en",
                "source": src["id"], "source_url": src["url"], "authority": src["publisher"],
                "state": src["region"] if src["region"] != "India" else None,
                "crop": ",".join(src["crops"])[:100]}
        try:
            out = post_file(args.api, ROOT / src["file"], meta)
        except urllib.error.HTTPError as exc:
            if exc.code == 409:  # same SHA-256 already in the knowledge base
                print(key, "-> already loaded")
                continue
            raise
        doc_id = out.get("document_id") or out.get("id")
        print(key, "->", {k: out.get(k) for k in ("document_id", "status", "message", "duplicate")})
        for _ in range(120):  # ingestion runs in the background; wait for it
            if doc_id is None:
                break
            doc = get(args.api, f"/documents/{doc_id}")
            if doc.get("status") not in ("pending", "processing", "PENDING", "PROCESSING"):
                print("   status", doc.get("status"), "| chunks", doc.get("chunk_count"),
                      "| error", doc.get("error_message"))
                break
            time.sleep(5)


if __name__ == "__main__":
    main()
