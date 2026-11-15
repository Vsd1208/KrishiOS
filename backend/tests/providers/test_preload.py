"""Startup model preload: loads providers with warm_up, never breaks startup."""

from types import SimpleNamespace

from app.config.settings import get_settings
from app.providers import preload


class _Sel:
    def __init__(self, provider=None, error=None):
        self.provider, self.error = provider, error

    def get(self, name):
        if self.error:
            raise self.error
        return self.provider


def test_warm_up_outcomes(monkeypatch) -> None:
    loaded = []
    ok = SimpleNamespace(warm_up=lambda: loaded.append("it2"))

    def boom():
        raise OSError("disk")

    monkeypatch.setattr(preload, "_configured", lambda s: [
        ("translation", "indictrans2", _Sel(ok)),
        ("translation", "mock", _Sel(SimpleNamespace())),
        ("stt", "indicconformer", _Sel(SimpleNamespace(warm_up=boom))),
        ("tts", "bad", _Sel(error=KeyError("bad"))),
    ])
    out = preload.warm_up_models(get_settings())
    assert loaded == ["it2"]
    assert out["translation:indictrans2"].startswith("loaded")
    assert out["translation:mock"] == "no local model"
    assert out["stt:indicconformer"].startswith("failed (OSError")
    assert out["tts:bad"].startswith("skipped")


def test_preload_disabled_by_default() -> None:
    off = get_settings().model_copy(update={"PRELOAD_MODELS": False})
    assert preload.start_preload(off) is None
