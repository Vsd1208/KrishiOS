"""WER/CER normalisation across scripts."""

from krishios_ml.voice.evaluation.wer import error_rates, normalize_for_wer


def test_normalisation_digits_punctuation_case() -> None:
    assert normalize_for_wer("Rain, 3 MM!") == "rain 3 mm"
    assert normalize_for_wer("वर्षा ३ मिमी।") == "वर्षा 3 मिमी"
    assert normalize_for_wer("వర్షం ౩ మి.మీ.") == "వర్షం 3 మి మీ"


def test_zero_width_joiners_ignored() -> None:
    assert normalize_for_wer("షెంగెన్‌లో") == normalize_for_wer("షెంగెన్లో")


def test_error_rates_corpus_level() -> None:
    r = error_rates(["a b c d", "e f"], ["a b x d", "e f"])
    assert r.wer == round(1 / 6, 4)
    assert r.n_utterances == 2 and r.n_ref_words == 6


def test_empty_references_skipped() -> None:
    assert error_rates(["", "a"], ["x", "a"]).n_utterances == 1
