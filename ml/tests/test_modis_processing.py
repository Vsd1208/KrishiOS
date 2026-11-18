"""MODIS monthly processing: file pairing and district means from small GeoTIFFs."""

import importlib.util
import io
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import box

from krishios_ml.yield_features import modis
from krishios_ml.yield_features.modis import use_bundled_proj

use_bundled_proj()
import rasterio  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("process_modis_ndvi",
                                              SCRIPTS / "process_modis_ndvi.py")
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)


def tif(path: Path, data: np.ndarray, nodata) -> Path:
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
                       count=1, dtype=data.dtype, crs="EPSG:4326", nodata=nodata,
                       transform=from_origin(80, 20, 1, 1)) as dst:
        dst.write(data, 1)
    return path


def test_a_cut_off_download_is_rejected_and_not_kept(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(modis.urllib.request, "urlopen",
                        lambda req, timeout: io.BytesIO(b"short"))
    file = {"file_id": "1", "file_name": "a/x.tif", "file_size": 100}
    with pytest.raises(OSError, match="incomplete download"):
        modis.download("token", "task", file, tmp_path)
    assert not (tmp_path / "a" / "x.tif").exists()
    assert modis.download("token", "task", {**file, "file_size": 5}, tmp_path).read_bytes() \
        == b"short"


def test_only_months_with_both_layers_are_used() -> None:
    stem = "x/MOD13A3.061_"
    files = [{"file_name": f"{stem}_1_km_monthly_NDVI_doy2000032000000_aid0001.tif"},
             {"file_name": f"{stem}_1_km_monthly_pixel_reliability_doy2000032000000_aid0001.tif"},
             {"file_name": f"{stem}_1_km_monthly_VI_Quality_doy2000032000000_aid0001.tif"},
             {"file_name": f"{stem}_1_km_monthly_NDVI_doy2000061000000_aid0001.tif"}]
    assert list(pm.month_pairs(files)) == [date(2000, 2, 1)]


def test_district_mean_uses_good_pixels_only(tmp_path) -> None:
    ndvi = tif(tmp_path / "n.tif", np.array([[0.2, 0.4], [0.9, -3000.0]], dtype="float32"), -3000)
    rel = tif(tmp_path / "r.tif", np.array([[0, 1], [3, 0]], dtype="int16"), -1)
    districts = gpd.GeoDataFrame({"lgd_district_code": [509]}, geometry=[box(80, 18, 82, 20)],
                                 crs=4326)
    table, index = pm.process_month(ndvi, rel, districts)
    assert index.shape == (2, 2) and table["lgd_district_code"].tolist() == [509]
    assert abs(float(table.loc[0, "ndvi"]) - 0.3) < 1e-6
    assert float(table.loc[0, "good_share"]) == 0.5
