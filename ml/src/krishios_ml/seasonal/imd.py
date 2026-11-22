"""IMD gridded daily data (Pai et al. 2014 rainfall; Srivastava et al. 2009 temperature).

Binary files of little-endian float32, one per year, laid out (day, latitude, longitude):

- rainfall: 0.25 deg, 129 latitudes 6.5-38.5 N x 135 longitudes 66.5-100 E; missing = -999;
- Tmax / Tmin: 1 deg, 31 latitudes 7.5-37.5 N x 31 longitudes 67.5-97.5 E; missing = 99.9.

The layout was checked on the 2000 file: Arabian Sea cells are all missing, and Kerala gets
2021 mm in June-September, Mumbai 2254 mm and Delhi 574 mm for the year.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class Grid:
    lat0: float
    lon0: float
    step: float
    nlat: int
    nlon: int
    missing_below: float | None = None  # values below this are missing
    missing_above: float | None = None  # values above this are missing

    @property
    def lats(self) -> np.ndarray:
        return self.lat0 + self.step * np.arange(self.nlat)

    @property
    def lons(self) -> np.ndarray:
        return self.lon0 + self.step * np.arange(self.nlon)


RAIN = Grid(6.5, 66.5, 0.25, 129, 135, missing_below=-998.0)
TEMP = Grid(7.5, 67.5, 1.0, 31, 31, missing_above=99.0)
GRID_OF = {"rain": RAIN, "tmax": TEMP, "tmin": TEMP}

# IMD meteorological seasons (months). JF belongs to the calendar year of January.
SEASONS = {"JJAS": (6, 7, 8, 9), "OND": (10, 11, 12), "JF": (1, 2), "MAM": (3, 4, 5)}


def read_year(path: Path, grid: Grid, year: int) -> np.ndarray:
    """(days, nlat, nlon) float32 with missing values as NaN."""
    data = np.fromfile(path, dtype="<f4")
    days = 366 if calendar.isleap(year) else 365
    if data.size != days * grid.nlat * grid.nlon:
        raise ValueError(f"{path.name}: {data.size} values, expected {days} days of "
                         f"{grid.nlat}x{grid.nlon}")
    data = data.reshape(days, grid.nlat, grid.nlon)
    if grid.missing_below is not None:
        data[data < grid.missing_below] = np.nan
    if grid.missing_above is not None:
        data[data > grid.missing_above] = np.nan
    return data


def month_of_day(year: int) -> np.ndarray:
    """Month (1-12) of each day of the year."""
    return np.concatenate([np.full(calendar.monthrange(year, m)[1], m) for m in range(1, 13)])


def season_cells(data: np.ndarray, year: int, variable: str) -> dict[str, np.ndarray]:
    """Per season, a (nlat, nlon) cell value: total rain (mm) or mean temperature (deg C).

    A cell is NaN for a season if any of its days in that season is missing, so a season total
    is never built from part of the days.
    """
    months = month_of_day(year)
    out: dict[str, np.ndarray] = {}
    for season, mm in SEASONS.items():
        days = data[np.isin(months, mm)]
        complete = ~np.isnan(days).any(axis=0)
        value = days.sum(axis=0) if variable == "rain" else days.mean(axis=0)
        out[season] = np.where(complete, value, np.nan)
    return out
