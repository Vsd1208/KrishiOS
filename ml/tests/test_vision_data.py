"""Vision data: near-duplicate grouping keeps copies of one photo in one split."""

import numpy as np
from PIL import Image

from krishios_ml.vision.data import dhash, near_duplicate_groups, split_groups


def _img(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 255, (64, 64, 3), dtype=np.uint8))


def test_resized_recompressed_copy_has_a_close_hash() -> None:
    a = _img(1)
    b = a.resize((200, 200)).resize((64, 64))
    assert bin(dhash(a) ^ dhash(b)).count("1") <= 6
    assert bin(dhash(a) ^ dhash(_img(2))).count("1") > 6


def test_near_duplicates_share_a_group_and_a_split() -> None:
    hashes = np.array([0b0, 0b111, 0xFFFF_0000_0000_0000, 0xFFFF_0000_0000_0001], dtype=np.uint64)
    g = near_duplicate_groups(hashes, max_bits=6)
    assert g[0] == g[1] and g[2] == g[3] and g[0] != g[2]
    s = split_groups(g, val=0.3, test=0.3, seed="t")
    assert s[0] == s[1] and s[2] == s[3]


def test_augmented_copies_of_one_photo_share_a_group() -> None:
    from krishios_ml.vision.data import (
        augmented_family_groups,
        connected_groups,
        grey_thumbnail,
    )

    a, b = _img(1), _img(2)
    flipped = a.transpose(Image.Transpose.ROTATE_90)
    names = ["BLAST1_001.jpg", "BLAST2_001.jpg", "BLAST1_002.jpg", "BLAST1_003.jpg"]
    thumbs = np.stack([grey_thumbnail(x) for x in (a, b, flipped, _img(3))])
    g = augmented_family_groups(names, ["Blast"] * 4, thumbs)
    assert g[0] == g[1] == g[2]  # same number; same pixels under a different number
    assert g[3] != g[0]
    other = augmented_family_groups(["X1_001.jpg", "X1_001.jpg"], ["Blast", "Tungro"],
                                    np.stack([grey_thumbnail(a), grey_thumbnail(b)]))
    assert other[0] != other[1]  # the same number in another class is another photo
    assert list(connected_groups(3, [np.array([1, 1, 2]), np.array(["a", "b", "b"])])) == [0, 0, 0]


def test_rice_split_is_stratified_and_guards_against_copies() -> None:
    from krishios_ml.vision.data import stratified_group_split, test_rows_matching_training

    groups = np.arange(100)
    labels = np.array(["a"] * 50 + ["b"] * 50)
    s = stratified_group_split(groups, labels, val=0.2, test=0.2, seed="t")
    for lab in ("a", "b"):
        assert (s[labels == lab] == "test").sum() == 10
        assert (s[labels == lab] == "val").sum() == 10
    big = stratified_group_split(np.array([0] * 80 + list(range(1, 21))), np.array(["a"] * 100),
                                 val=0.2, test=0.2, seed="t")
    assert set(big[:80]) == {"train"} and (big[80:] == "test").sum() == 4  # 20% of the 20 left
    h = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    hit = test_rows_matching_training(h, np.array(["a", "a", "a"]),
                                      np.array(["test", "train", "test"]))
    assert hit.tolist() == [True, False, False]
