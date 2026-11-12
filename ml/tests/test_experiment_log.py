"""Tests for the JSONL experiment log."""

from krishios_ml.common.experiment_log import read_records, track_experiment
from krishios_ml.common.seed import seed_everything


def test_track_experiment_appends_record(tmp_path) -> None:
    log = tmp_path / "exp.jsonl"
    with track_experiment("unit", {"lr": 0.1}, seed=seed_everything(7), split_id="s1",
                          log_path=log) as rec:
        rec.metrics["mae"] = 1.5
        rec.artifact_path = "artifacts/x"
    records = read_records(log)
    assert len(records) == 1
    r = records[0]
    assert r["config"] == {"lr": 0.1} and r["seed"] == 7 and r["split_id"] == "s1"
    assert r["metrics"]["mae"] == 1.5 and r["wall_clock_s"] is not None
    assert r["git_commit"]
