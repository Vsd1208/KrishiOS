"""Large-scale climate drivers for yield forecasts (Phase 10).

Monthly indices that describe conditions far from the farm and can influence the Indian monsoon
and winter rains:

- ``nino34``: equatorial Pacific sea-surface temperature anomaly (NOAA CPC OISST, satellite based);
- ``dmi``: Indian Ocean Dipole Mode Index (NOAA PSL, HadISST);
- ``olr``: standardized outgoing longwave radiation at the equator, 160E-160W (NOAA CPC; a
  satellite measure related to tropical cloud and convection);
- ``soi``: Southern Oscillation Index (NOAA CPC, surface pressure);
- ``tna``: Tropical North Atlantic SST index (NOAA PSL).

Leakage rule: a month is usable only if its end plus ``PUBLICATION_LAG_DAYS`` is strictly before
the forecast cutoff. Historical release dates are not recorded, so the lag is deliberately long.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PUBLICATION_LAG_DAYS = 30
INDICES = ("nino34", "dmi", "olr", "soi", "tna")
STATS = ("last", "mean3", "change3")
FEATURES = [f"clim_{i}_{s}" for i in INDICES for s in STATS]
MISSING_ABS = 99.0


def _rows(years: list[int], values: list[list[float]], name: str) -> pd.DataFrame:
    out = [(name, pd.Timestamp(y, m + 1, 1), v) for y, row in zip(years, values, strict=True)
           for m, v in enumerate(row) if abs(v) < MISSING_ABS]
    return pd.DataFrame(out, columns=["index", "month_start", "value"])


def parse_year_table(text: str, name: str) -> pd.DataFrame:
    """Lines of ``year`` followed by 12 monthly values (NOAA PSL format)."""
    years, values = [], []
    for line in text.splitlines():
        p = line.split()
        if len(p) == 13 and re.fullmatch(r"\d{4}", p[0]):
            try:
                row = [float(x) for x in p[1:]]
            except ValueError:
                continue
            years.append(int(p[0]))
            values.append(row)
    return _rows(years, values, name)


def parse_sstoi(text: str, column: str = "NINO3.4", name: str = "nino34") -> pd.DataFrame:
    """CPC ``sstoi.indices``: the anomaly column that follows ``column``."""
    lines = text.splitlines()
    head = lines[0].split()
    j = head.index(column) + 1  # the ANOM column after it
    rows = []
    for line in lines[1:]:
        p = line.split()
        if len(p) == len(head):
            v = float(p[j])
            if abs(v) < MISSING_ABS:
                rows.append((name, pd.Timestamp(int(p[0]), int(p[1]), 1), v))
    return pd.DataFrame(rows, columns=["index", "month_start", "value"])


def parse_olr(text: str, name: str = "olr") -> pd.DataFrame:
    """CPC ``olr``: fixed-width table; only the STANDARDIZED section is read."""
    years, values, active = [], [], False
    for line in text.splitlines():
        if "STANDARDIZED" in line:
            active = True
        elif active and re.match(r"\d{4}", line) and len(line.rstrip()) >= 76:
            years.append(int(line[:4]))
            values.append([float(line[4 + 6 * m:10 + 6 * m]) for m in range(12)])
    return _rows(years, values, name)


def load_indices(folder: Path) -> pd.DataFrame:
    def read(name: str) -> str:
        return (folder / name).read_text(encoding="utf-8", errors="replace")

    parts = [parse_sstoi(read("sstoi.txt")), parse_year_table(read("dmi.txt"), "dmi"),
             parse_olr(read("olr.txt")), parse_year_table(read("soi.txt"), "soi"),
             parse_year_table(read("tna.txt"), "tna")]
    return pd.concat(parts, ignore_index=True)


@dataclass(frozen=True)
class Driver:
    """A monthly field averaged over a box, and the states it is expected to influence."""

    name: str
    dataset: str
    variable: str
    level: float | None
    lat: tuple[float, float]
    lon: tuple[float, float]
    states: frozenset[int] | None  # None = every state
    lag_days: int = 30


NCEP = "ncep.reanalysis/Monthlies/pressure/{}.mon.mean.nc"
GPCP, OLR, SST = ("gpcp/precip.mon.mean.nc", "interp_OLR/olr.mon.mean.nc",
                  "noaa.oisst.v2/sst.mnmean.nc")
NORTHWEST = frozenset({3, 4, 6, 8})  # Punjab, Chandigarh, Haryana, Rajasthan
WEST_HIMALAYA = frozenset({1, 2, 5, 37})  # J&K, Himachal, Uttarakhand, Ladakh
GANGA_EAST = frozenset({9, 10})  # Uttar Pradesh, Bihar
NORTHEAST = frozenset({11, 12, 13, 14, 15, 16, 17, 18})  # Sikkim and the north-eastern states
REGIONS = {"northwest": NORTHWEST, "west_himalaya": WEST_HIMALAYA, "ganga_east": GANGA_EAST,
           "northeast": NORTHEAST}
WESTERLY = NORTHWEST | WEST_HIMALAYA
DRIVERS = (
    # Upper-level westerlies and troughs linked to western disturbances.
    Driver("u200_middle_east", NCEP.format("uwnd"), "uwnd", 200, (25, 40), (35, 60), WESTERLY),
    Driver("u200_central_asia", NCEP.format("uwnd"), "uwnd", 200, (35, 50), (55, 80), WESTERLY),
    Driver("z500_central_asia", NCEP.format("hgt"), "hgt", 500, (35, 50), (55, 80), WESTERLY),
    # Rain falling upstream of the Ganga plains and the Brahmaputra.
    Driver("rain_nepal", GPCP, "precip", None, (26, 31), (80, 88.5), GANGA_EAST, 90),
    Driver("rain_upper_brahmaputra", GPCP, "precip", None, (27, 32), (88, 97), NORTHEAST, 90),
    # Heat over the high Himalaya and Tibetan Plateau (near the 500 hPa surface there).
    Driver("t500_tibet_east", NCEP.format("air"), "air", 500, (27, 35), (85, 100), NORTHEAST),
    Driver("t500_tibet_west", NCEP.format("air"), "air", 500, (30, 38), (75, 90), WEST_HIMALAYA),
    # Monsoon circulation, tropical cloud and neighbouring seas: relevant across India.
    Driver("u850_somali_jet", NCEP.format("uwnd"), "uwnd", 850, (5, 15), (50, 70), None),
    Driver("u200_easterly_jet", NCEP.format("uwnd"), "uwnd", 200, (5, 20), (50, 90), None),
    Driver("olr_bay_of_bengal", OLR, "olr", None, (5, 20), (80, 95), None),
    Driver("olr_arabian_sea", OLR, "olr", None, (5, 20), (55, 75), None),
    Driver("sst_bay_of_bengal", SST, "sst", None, (5, 20), (80, 95), None),
    Driver("sst_arabian_sea", SST, "sst", None, (5, 20), (55, 75), None),
    Driver("sst_equatorial_indian", SST, "sst", None, (-10, 10), (50, 100), None),
)
DRIVER_STATS = ("last", "mean3")
DRIVER_FEATURES = [f"drv_{d.name}_{s}" for d in DRIVERS for s in DRIVER_STATS]
BASELINE_YEARS = (1982, 2009)  # ends before the first evaluation period


def parse_dods_vector(text: str, name: str) -> np.ndarray:
    """A 1-D variable from an OPeNDAP ``.ascii`` response."""
    m = re.search(rf"(?m)^(?:\w+\.)?{re.escape(name)}\[\d+\]\s*\n([^\n]+)", text)
    if not m:
        raise ValueError(f"{name} not found in response")
    return np.array([float(x) for x in m.group(1).split(",")])


def parse_dods_grid(text: str, variable: str) -> np.ndarray:
    """The data array of an OPeNDAP ``.ascii`` response, in its stated shape."""
    m = re.search(rf"(?m)^{re.escape(variable)}\.{re.escape(variable)}((?:\[\d+\])+)\s*$", text)
    if not m:
        raise ValueError(f"{variable} grid not found in response")
    shape = [int(x) for x in re.findall(r"\d+", m.group(1))]
    values: list[float] = []
    for line in text[m.end():].splitlines():
        if not line.strip():
            if values:
                break
            continue
        values.extend(float(x) for x in line.split(",")[1:])
    data = np.array(values, dtype="float64")
    if data.size != int(np.prod(shape)):
        raise ValueError(f"{variable}: expected {int(np.prod(shape))} values, got {data.size}")
    return data.reshape(shape)


def box_mean(grid: np.ndarray, lat: np.ndarray, missing: float | None = None) -> np.ndarray:
    """Area-weighted mean over the last two axes (lat, lon), ignoring missing cells."""
    bad = ~np.isfinite(grid) | (np.abs(grid) > 1e30)
    if missing is not None:
        bad |= grid == missing
    w = np.broadcast_to(np.cos(np.deg2rad(lat))[None, :, None], grid.shape).copy()
    w[bad] = 0.0
    total = w.sum(axis=(1, 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total > 0, (np.where(bad, 0, grid) * w).sum(axis=(1, 2)) / total, np.nan)


def standardize(series: pd.DataFrame) -> pd.DataFrame:
    """Add ``z``: the anomaly from each driver's calendar-month normal, in standard deviations,
    with normals taken only from ``BASELINE_YEARS``."""
    d = series.assign(month_start=pd.to_datetime(series["month_start"]))
    d["month"] = d["month_start"].dt.month
    base = d[d["month_start"].dt.year.between(*BASELINE_YEARS)]
    n = base.groupby(["driver", "month"])["value"].agg(["mean", "std"]).reset_index()
    d = d.merge(n, on=["driver", "month"], how="left")
    d["z"] = (d["value"] - d["mean"]) / d["std"].where(d["std"] > 0)
    return d.drop(columns=["month", "mean", "std"])


def driver_features(series: pd.DataFrame, cutoffs: pd.Series) -> pd.DataFrame:
    """Latest and 3-month mean anomaly of each driver, from published months only."""
    m = series.assign(end=pd.to_datetime(series["month_start"]) + pd.offsets.MonthEnd(0))
    groups = {k: g.sort_values("end") for k, g in m.groupby("driver")}
    rows = []
    for cutoff in pd.to_datetime(pd.Series(cutoffs).drop_duplicates()):
        row: dict = {"cutoff": cutoff}
        for d in DRIVERS:
            g = groups.get(d.name)
            v = np.array([], dtype=float)
            if g is not None:
                ok = (g["end"] + pd.Timedelta(days=d.lag_days) < cutoff) & (
                    g["end"] >= cutoff - pd.DateOffset(months=13))
                v = g.loc[ok, "z"].dropna().to_numpy(dtype=float)
            row[f"drv_{d.name}_last"] = v[-1] if len(v) else np.nan
            row[f"drv_{d.name}_mean3"] = v[-3:].mean() if len(v) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def route_drivers(df: pd.DataFrame) -> pd.DataFrame:
    """Blank each regional driver outside the states it is expected to influence."""
    out = df.copy()
    state = out["lgd_state_code"].astype(int)
    for d in DRIVERS:
        if d.states is not None:
            outside = ~state.isin(d.states)
            for s in DRIVER_STATS:
                out.loc[outside, f"drv_{d.name}_{s}"] = np.nan
    return out


def features_at(indices: pd.DataFrame, cutoffs: pd.Series) -> pd.DataFrame:
    """One row per unique cutoff: latest value, mean of the last 3 available months, and change
    from 3 months earlier, using only months published before the cutoff."""
    m = indices.assign(end=pd.to_datetime(indices["month_start"]) + pd.offsets.MonthEnd(0))
    series = {k: g.sort_values("end") for k, g in m.groupby("index")}
    lag = pd.Timedelta(days=PUBLICATION_LAG_DAYS)
    rows = []
    for cutoff in pd.to_datetime(pd.Series(cutoffs).drop_duplicates()):
        row: dict = {"cutoff": cutoff}
        for name in INDICES:
            g = series.get(name)
            v = np.array([], dtype=float)
            if g is not None:
                ok = (g["end"] + lag < cutoff) & (g["end"] >= cutoff - pd.DateOffset(months=13))
                v = g.loc[ok, "value"].to_numpy(dtype=float)
            row[f"clim_{name}_last"] = v[-1] if len(v) else np.nan
            row[f"clim_{name}_mean3"] = v[-3:].mean() if len(v) else np.nan
            row[f"clim_{name}_change3"] = v[-1] - v[-4] if len(v) >= 4 else np.nan
        rows.append(row)
    return pd.DataFrame(rows)
