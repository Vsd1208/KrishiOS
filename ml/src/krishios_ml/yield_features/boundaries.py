"""District polygons keyed by LGD code (Phase 7).

Source: geoBoundaries IND ADM2 (2021 vintage, built from lgdirectory.gov.in, ODbL 1.0) for the
polygons, and geoBoundaries IND ADM1 (2011, CC BY 2.5 IN) to know each polygon's state. The
ADM2 file has names only, so each polygon is matched to LGD by (state, normalised name):

1. the polygon's state is the ADM1 state containing its representative point;
2. a name matches when it equals the LGD district name, an alias from
   ``reference/district_aliases.csv``, or a spelling with spaces/punctuation removed;
3. the 2011 state layer predates Telangana (2014) and Ladakh (2019), so those states are
   treated as part of their parent state when comparing.

Every match records its method; unmatched LGD districts are listed for manual review, never
guessed. Polygons are used internally for zonal statistics and are not redistributed.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

import pandas as pd

STATE_PARENTS = {
    "telangana": "andhra pradesh",
    "ladakh": "jammu and kashmir",
    "the dadra and nagar haveli and daman and diu": "dadra and nagar haveli",
    "dadra and nagar haveli and daman and diu": "dadra and nagar haveli",
    "daman and diu": "dadra and nagar haveli",
}


def norm(text: str) -> str:
    """Lower-case, strip diacritics ("Himāchal" -> "himachal"), '&' -> 'and', punctuation -> ' '."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def compact(text: str) -> str:
    return norm(text).replace(" ", "")


def state_key(name: str) -> str:
    n = norm(name)
    return STATE_PARENTS.get(n, n)


def load_polygons(adm2: Path, adm1: Path):
    import geopandas as gpd

    districts = gpd.read_file(adm2)[["shapeName", "shapeID", "geometry"]].to_crs(4326)
    states = (
        gpd.read_file(adm1)[["shapeName", "geometry"]]
        .rename(columns={"shapeName": "state_2011"})
        .to_crs(4326)
    )
    points = districts.copy()
    points["geometry"] = districts.geometry.representative_point()
    joined = gpd.sjoin(points, states, how="left", predicate="within")
    districts["state_2011"] = joined["state_2011"].values
    return districts


FUZZY_MIN = 0.80


def _fuzzy(matches: pd.DataFrame, lgd: pd.DataFrame) -> None:
    """Spelling variants (Ahmadabad/Ahmedabad, Dohad/Dahod): within the same state, among LGD
    districts not matched exactly, take the best similarity >= FUZZY_MIN if it is unique.
    The score is recorded (``fuzzy:0.91``) so a reviewer can check every one."""
    from difflib import SequenceMatcher

    taken = set(matches["lgd_district_code"].dropna().astype(int))
    free = lgd[~lgd["lgd_district_code"].isin(taken)]
    by_state: dict[str, list[tuple[int, str]]] = {}
    for r in free.itertuples():
        by_state.setdefault(state_key(r.state_name), []).append(
            (int(r.lgd_district_code), compact(r.district_name))
        )
    for i in matches.index[matches["match"] == "unmatched"]:
        st = matches.at[i, "state_2011"]
        if not isinstance(st, str):
            continue
        name = compact(matches.at[i, "shape_name"])
        scored = sorted(
            (
                (SequenceMatcher(None, name, cand).ratio(), code)
                for code, cand in by_state.get(state_key(st), [])
            ),
            reverse=True,
        )
        if (
            scored
            and scored[0][0] >= FUZZY_MIN
            and (len(scored) == 1 or scored[1][0] < scored[0][0] - 0.05)
        ):
            score, code = scored[0]
            if code not in taken:
                matches.at[i, "lgd_district_code"] = code
                matches.at[i, "match"] = f"fuzzy:{score:.2f}"
                taken.add(code)


def _apply_overrides(matches: pd.DataFrame, overrides: pd.DataFrame, valid: set[int]) -> None:
    """Reviewed (state, polygon name) -> LGD code pairs for official renames and Odia
    transliterations that no string similarity can find (Gurgaon -> Gurugram, Cuttack ->
    Kataka). They win over automatic matches; each is recorded as ``override:<relation>``.
    ``predecessor`` means the polygon predates a split, so it covers more than the LGD
    district does today."""
    want = {}
    for r in overrides.itertuples():
        code = int(r.lgd_district_code)
        if code not in valid:
            raise ValueError(f"override {r.shape_name}: LGD code {code} not in the reference")
        want[(state_key(r.state_2011), compact(r.shape_name))] = (code, r.relation)
    used = set()
    for i in matches.index:
        st = matches.at[i, "state_2011"]
        key = (state_key(st) if isinstance(st, str) else "", compact(matches.at[i, "shape_name"]))
        if key in want:
            code, relation = want[key]
            matches.at[i, "lgd_district_code"] = code
            matches.at[i, "match"] = f"override:{relation}"
            used.add(key)
    if missing := set(want) - used:
        raise ValueError(f"overrides matched no polygon: {sorted(missing)}")


def match_lgd(
    districts, lgd_csv: Path, alias_csv: Path | None = None, override_csv: Path | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lgd = pd.read_csv(lgd_csv)
    aliases: dict[str, list[str]] = {}
    if alias_csv and alias_csv.exists():
        with alias_csv.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                aliases.setdefault(str(int(row["lgd_district_code"])), []).append(row["alias"])
    index: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for r in lgd.itertuples():
        names = [r.district_name, *aliases.get(str(r.lgd_district_code), [])]
        for i, name in enumerate(names):
            method = "name" if i == 0 else "alias"
            for key in {norm(name), compact(name)}:
                index.setdefault((state_key(r.state_name), key), []).append(
                    (int(r.lgd_district_code), method)
                )
    rows = []
    for d in districts.itertuples():
        st = state_key(d.state_2011) if isinstance(d.state_2011, str) else ""
        hits = index.get((st, norm(d.shapeName))) or index.get((st, compact(d.shapeName))) or []
        codes = sorted({c for c, _ in hits})
        rows.append(
            {
                "shapeID": d.shapeID,
                "shape_name": d.shapeName,
                "state_2011": d.state_2011,
                "lgd_district_code": codes[0] if len(codes) == 1 else None,
                "match": (hits[0][1] if len(codes) == 1 else "ambiguous" if codes else "unmatched"),
            }
        )
    matches = pd.DataFrame(rows)
    if override_csv and override_csv.exists():
        _apply_overrides(matches, pd.read_csv(override_csv), set(lgd["lgd_district_code"]))
    _fuzzy(matches, lgd)
    matched_codes = set(matches["lgd_district_code"].dropna().astype(int))
    unmatched_lgd = lgd[~lgd["lgd_district_code"].isin(matched_codes)][
        ["lgd_district_code", "district_name", "state_name"]
    ]
    return matches, unmatched_lgd
