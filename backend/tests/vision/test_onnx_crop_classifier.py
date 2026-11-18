"""ONNX crop classifier decision logic (fake ONNX session; no model file needed)."""

import numpy as np
from app.vision.providers.onnx_crop_classifier import OnnxCropClassifier, resolve_threshold
from PIL import Image

LABELS = {
    "model_name": "krishios-vision-test", "model_version": "t1", "image_size": 32,
    "mean": [0.5, 0.5, 0.5], "std": [0.25, 0.25, 0.25],
    "temperature": {"crop": 1.0, "condition": 1.0},
    "crops": [{"label": "tomato", "crop_canonical": "tomato", "supported": True},
              {"label": "bell_pepper", "crop_canonical": None, "supported": False},
              {"label": "paddy", "crop_canonical": "paddy", "supported": True}],
    "conditions": [
        {"label": "tomato|early_blight", "crop": "tomato", "name": "early blight",
         "healthy": False},
        {"label": "tomato|healthy", "crop": "tomato", "name": "healthy", "healthy": True},
        {"label": "bell_pepper|bacterial_spot", "crop": "bell_pepper",
         "name": "bacterial spot", "healthy": False},
        {"label": "paddy|blast", "crop": "paddy", "name": "blast", "healthy": False},
    ],
    "license": "test",
}


class FakeSession:
    def __init__(self, crop, cond):
        self.out = [np.array([crop], dtype=np.float32), np.array([cond], dtype=np.float32)]

    def run(self, names, feeds):
        assert feeds["image"].shape == (1, 3, 32, 32)
        return self.out


def model(crop, cond, threshold=0.6) -> OnnxCropClassifier:
    m = OnnxCropClassifier.__new__(OnnxCropClassifier)
    m._labels, m._threshold = LABELS, threshold
    m._crops, m._conds = LABELS["crops"], LABELS["conditions"]
    m._crop_of_cond = np.array([c["crop"] for c in LABELS["conditions"]])
    m._session = FakeSession(crop, cond)
    return m


def photo(tmp_path):
    p = tmp_path / "leaf.jpg"
    Image.new("RGB", (64, 48), (40, 120, 40)).save(p)
    return p


def test_confident_supported_crop_is_detected_with_its_conditions(tmp_path) -> None:
    r = model([5.0, 0.0, 0.0], [3.0, 0.0, 9.0, 9.0]).classify(photo(tmp_path))
    assert r.crop_detected == "tomato" and r.crop_supported
    assert r.crop_candidates[0][0] == "tomato"
    # Only tomato conditions are read, even though other crops' logits are higher.
    assert [c.name for c in r.candidate_conditions] == ["early blight", "healthy"]


def test_uncertain_crop_asks_the_farmer(tmp_path) -> None:
    r = model([0.2, 0.0, 0.1], [0.0, 0.0, 0.0, 0.0]).classify(photo(tmp_path))
    assert r.crop_detected is None and not r.crop_supported
    assert len(r.crop_candidates) == 3


def test_unsupported_crop_is_never_auto_accepted(tmp_path) -> None:
    r = model([0.0, 8.0, 0.0], [0.0, 0.0, 5.0, 0.0]).classify(photo(tmp_path))
    assert r.crop_candidates[0][0] == "other:bell_pepper"
    assert not r.crop_supported and r.crop_detected is None


def test_artifact_threshold_wins_and_null_means_always_ask(tmp_path) -> None:
    assert resolve_threshold({}, 0.6) == 0.6
    assert resolve_threshold({"confirm_threshold": 0.83}, 0.6) == 0.83
    never = resolve_threshold({"confirm_threshold": None}, 0.6)
    r = model([50.0, 0.0, 0.0], [3.0, 0.0, 0.0, 0.0], threshold=never).classify(photo(tmp_path))
    assert r.crop_detected is None and not r.crop_supported


def test_phone_rotation_is_applied_before_inference(tmp_path) -> None:
    img = Image.new("RGB", (64, 64), (0, 255, 0))
    img.paste((255, 0, 0), (0, 0, 64, 32))  # red on top as stored
    exif = Image.Exif()
    exif[0x0112] = 6  # display rotated 90 degrees clockwise: the top becomes the right side
    p = tmp_path / "phone.jpg"
    img.save(p, exif=exif, quality=95)
    red = model([0.0, 0.0, 0.0], [0.0] * 4)._tensor(p)[0, 0]
    assert red[:, -4:].mean() > red[:, :4].mean() + 1.0


def test_confirmed_crop_overrides_the_prediction(tmp_path) -> None:
    r = model([5.0, 0.0, 0.0], [3.0, 0.0, 0.0, 1.0]).classify(photo(tmp_path),
                                                            confirmed_crop="paddy")
    assert r.crop_detected == "paddy"
    assert [c.name for c in r.candidate_conditions] == ["blast"]
