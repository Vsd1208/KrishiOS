"""Build ``ml/reference/lgd_districts.csv`` and ``lgd_blocks.csv`` from an LGD snapshot.

Source: Local Government Directory (Ministry of Panchayati Raj), licence GODL-India,
via the daily Parquet mirror at https://ramseraph.github.io/opendata/lgd/ which records
its source date per dataset. Usage::

    uv run python -m krishios_ml.reference.build_lgd_reference \
        --districts <districts.parquet> --blocks <blocks.parquet> --observed-on 2026-11-12
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from loguru import logger

from krishios_ml.common.paths import REFERENCE_DIR

DISTRICT_COLUMNS = {
    "district_code": "lgd_district_code",
    "district_name": "district_name",
    "state_code": "lgd_state_code",
    "state_name": "state_name",
    "district_census_2001_code": "census_2001_code",
    "district_census_2011_code": "census_2011_code",
}
BLOCK_COLUMNS = {
    "block_code": "lgd_block_code",
    "block_version": "block_version",
    "block_name": "block_name",
    "block_name_local": "block_name_local",
    "district_code": "lgd_district_code",
    "state_code": "lgd_state_code",
}


def build(districts: Path, blocks: Path, observed_on: str, out_dir: Path = REFERENCE_DIR) -> None:
    """Write sorted, de-duplicated reference CSVs with the source date column."""
    d = pd.read_parquet(districts)[list(DISTRICT_COLUMNS)].rename(columns=DISTRICT_COLUMNS)
    b = pd.read_parquet(blocks)[list(BLOCK_COLUMNS)].rename(columns=BLOCK_COLUMNS)
    # LGD keeps historical versions of a block under the same code; keep the latest.
    b["lgd_block_code"] = b["lgd_block_code"].astype(int)
    n_before = len(b)
    b = b.sort_values(["lgd_block_code", "block_version"]).drop_duplicates(
        "lgd_block_code", keep="last"
    )
    logger.info("blocks: kept latest version for {} of {} rows", len(b), n_before)
    for frame, key in ((d, "lgd_district_code"), (b, "lgd_block_code")):
        frame[key] = frame[key].astype(int)
        if frame[key].duplicated().any():
            raise ValueError(f"duplicate {key} in LGD snapshot")
        frame["source_observed_on"] = observed_on
    d = d.sort_values("lgd_district_code")
    b = b.sort_values("lgd_block_code")
    orphan = set(b.lgd_district_code.astype(int)) - set(d.lgd_district_code)
    if orphan:
        logger.warning(
            "{} block rows reference unknown districts: {}", len(orphan), sorted(orphan)[:10]
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    d.to_csv(out_dir / "lgd_districts.csv", index=False)
    b.to_csv(out_dir / "lgd_blocks.csv", index=False)
    logger.info("wrote {} districts, {} blocks (observed {})", len(d), len(b), observed_on)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--districts", type=Path, required=True)
    parser.add_argument("--blocks", type=Path, required=True)
    parser.add_argument("--observed-on", required=True)
    args = parser.parse_args()
    build(args.districts, args.blocks, args.observed_on)


if __name__ == "__main__":
    main()
