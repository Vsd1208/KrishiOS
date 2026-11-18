"""Field recalibration helpers."""

import numpy as np

from krishios_ml.vision import metrics as vm


def test_threshold_is_the_lowest_that_reaches_the_target() -> None:
    conf = np.array([0.55] * 40 + [0.8] * 40)
    correct = np.array([False] * 40 + [True] * 40)
    assert vm.confidence_threshold(conf, correct, target=0.95) == 0.56


def test_threshold_needs_enough_rows_and_may_not_exist() -> None:
    conf, correct = np.array([0.9] * 10), np.array([True] * 10)
    assert vm.confidence_threshold(conf, correct, min_rows=30) is None
    assert vm.confidence_threshold(np.array([0.9] * 40), np.array([False] * 40)) is None


def test_temperature_handles_logits_masked_to_one_crop() -> None:
    logits = np.array([[4.0, 0.0, -np.inf], [0.0, 4.0, -np.inf], [4.0, 0.0, -np.inf]])
    t = vm.fit_temperature(logits, np.array([0, 1, 1]))
    p = vm.softmax(logits, t)
    assert np.isfinite(t) and np.allclose(p.sum(axis=1), 1.0) and (p[:, 2] == 0).all()
