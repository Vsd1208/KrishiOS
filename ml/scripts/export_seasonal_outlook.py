"""Phase 10d: export the district seasonal outlook for the backend (officer view).

Method frozen on the development years (dev run ``DEV_RUN``): recent normals, last 15 years,
shrunk toward 1/3 each. Skill per season and variable comes from the one-time test
(``TEST_RUN``, 2006-2024) and sets what the app shows:

- ``show``: test RPSS >= 0.05;
- ``weak``: 0.02 <= RPSS < 0.05, shown with a "weak signal" label;
- ``withhold``: RPSS < 0.02, not shown; the app says there is no reliable signal and points to IMD.

These thresholds are a display policy fixed when the export was written; they do not change any
forecast. Writes ``ml/artifacts/seasonal/<version>/{outlook.json, manifest.json}``.

Usage (from ml/)::

    python scripts/export_seasonal_outlook.py
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import _bootstrap  # noqa: F401
import pandas as pd

from krishios_ml.common.experiment_log import track_experiment
from krishios_ml.common.paths import ARTIFACTS_DIR, DATA_DIR, ML_ROOT, REPORTS_DIR
from krishios_ml.seasonal.outlook import ISSUE_MONTH, Config, outlook_next

TABLE = DATA_DIR / "processed" / "seasonal" / "v1" / "district_seasons.parquet"
DEV_RUN, TEST_RUN = "8f5bc6a3189e", "7ffb0cc22c5f"
SHOW, WEAK = 0.05, 0.02
SEASON_NAMES = {"JJAS": "June-September (monsoon / kharif)",
                "OND": "October-December (post-monsoon)",
                "JF": "January-February (winter / rabi)", "MAM": "March-May (pre-monsoon / zaid)"}
UNITS = {"rain": "mm", "tmax": "deg C", "tmin": "deg C"}


def display_of(rpss: float) -> str:
    return "show" if rpss >= SHOW else ("weak" if rpss >= WEAK else "withhold")


def main() -> None:
    dev = json.loads((REPORTS_DIR / "data" / f"seasonal_outlook_dev_{DEV_RUN}.json")
                     .read_text(encoding="utf-8"))
    test = json.loads((REPORTS_DIR / "data" / f"seasonal_outlook_test_{TEST_RUN}.json")
                      .read_text(encoding="utf-8"))
    settings = dev["best"]["config"]
    if test["config"]["settings"] != settings:
        raise SystemExit("the test run used other settings than the dev choice")
    cfg = Config(**settings)
    table = pd.read_parquet(TABLE)
    names = pd.read_csv(ML_ROOT / "reference" / "lgd_districts.csv").set_index(
        "lgd_district_code")["district_name"]
    data_through = int(table["year"].max())
    generated = datetime.now(UTC)
    version = f"seasonal-ocn{cfg.n_recent}-{data_through}-{generated:%Y%m%d%H%M}"
    config = {"settings": settings, "dev_run": DEV_RUN, "test_run": TEST_RUN,
              "data_through": data_through, "display": {"show": SHOW, "weak": WEAK}}
    with track_experiment("seasonal_outlook_export", config, seed=None,
                          split_id="hindcast-expanding") as rec:
        rows, seasons = [], {}
        for season in ISSUE_MONTH:
            sub = table[table["season"] == season]
            regions = sub.drop_duplicates("lgd_district_code").set_index("lgd_district_code")[
                "state"]
            variables = {}
            for variable in ("rain", "tmax", "tmin"):
                rpss = float(test["scores"][f"{season}/{variable}"]["rpss"])
                variables[variable] = {"unit": UNITS[variable], "test_rpss": rpss,
                                       "display": display_of(rpss)}
                values = sub.pivot(index="lgd_district_code", columns="year",
                                   values=variable).dropna(how="all")
                out = outlook_next(values, regions.reindex(values.index).fillna("").to_numpy(),
                                   cfg)
                for r in out.itertuples(index=False):
                    rows.append({"lgd_district_code": int(r.district),
                                 "district": names.get(int(r.district), str(r.district)),
                                 "state": regions.get(r.district) or None, "season": season,
                                 "variable": variable,
                                 "p_below": round(float(r.p_below), 3),
                                 "p_near": round(float(r.p_near), 3),
                                 "p_above": round(float(r.p_above), 3),
                                 "lower_tercile": round(float(r.lower_tercile), 1),
                                 "upper_tercile": round(float(r.upper_tercile), 1)})
            seasons[season] = {"name": SEASON_NAMES[season], "issue_month": ISSUE_MONTH[season],
                               "variables": variables}
        body = {"version": version, "generated_at": generated.isoformat(timespec="seconds"),
                "method": "recent normals: tercile frequencies of the last "
                          f"{cfg.n_recent} years, shrunk toward 1/3 each (k={cfg.k})",
                "history": [int(table["year"].min()), data_through],
                "data_through": data_through, "dev_run": DEV_RUN, "test_run": TEST_RUN,
                "seasons": seasons, "rows": rows}
        dest = ARTIFACTS_DIR / "seasonal" / version
        dest.mkdir(parents=True, exist_ok=True)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        (dest / "outlook.json").write_bytes(data)
        manifest = {"version": version, "generated_at": body["generated_at"],
                    "sha256": hashlib.sha256(data).hexdigest(), "rows": len(rows),
                    "data_through": data_through, "export_run": rec.run_id}
        (dest / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        rec.metrics = {"rows": len(rows), "display": {f"{s}/{v}": d["display"]
                                                      for s, x in seasons.items()
                                                      for v, d in x["variables"].items()}}
        rec.artifact_path = str(dest.relative_to(ML_ROOT))
    print(json.dumps(rec.metrics, indent=1))
    print("wrote", dest)


if __name__ == "__main__":
    main()
