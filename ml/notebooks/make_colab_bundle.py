"""Build ml/notebooks/krishios_colab_bundle.zip from the committed HEAD.

Contains code and evaluation sets only (backend/app, ml/src, ml/scripts, ml/evaluation_sets,
ml/reference) plus BUNDLE_COMMIT. No .env, secrets or data. Usage (repo root)::

    python ml/notebooks/make_colab_bundle.py
"""

import io
import subprocess
import tarfile
import zipfile
from pathlib import Path

PATHS = ["backend/app", "ml/src", "ml/scripts", "ml/evaluation_sets", "ml/reference"]


def main() -> None:
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
    commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                                     text=True).strip()
    tar_bytes = subprocess.check_output(["git", "archive", "--format=tar", "HEAD", *PATHS],
                                        cwd=root)
    out = root / "ml" / "notebooks" / "krishios_colab_bundle.zip"
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar, \
            zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for member in tar.getmembers():
            if member.isfile():
                data = tar.extractfile(member).read()  # type: ignore[union-attr]
                zf.writestr(member.name, data)
        zf.writestr("BUNDLE_COMMIT", commit + "\n")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB) from commit {commit}")


if __name__ == "__main__":
    main()
