import io

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from eval.conditions import CONDITIONS, apply, jpeg_bytes  # noqa: E402
from eval.make_docs import DOCS  # noqa: E402


def page():
    img = Image.new("RGB", (400, 560), "white")
    for y in range(40, 520, 24):
        img.paste((30, 30, 30), (40, y, 360, y + 6))
    return img


def test_every_condition_is_repeatable_and_changes_the_photo():
    clean = jpeg_bytes(apply(page(), "clean", 1), "clean")
    for cond in CONDITIONS[1:]:
        a = jpeg_bytes(apply(page(), cond, 7), cond)
        assert a == jpeg_bytes(apply(page(), cond, 7), cond)          # same seed, same photo
        assert a != clean
        w, h = Image.open(io.BytesIO(a)).size
        assert 300 <= w <= 900 and 400 <= h <= 1300


def test_documents_are_fictitious_and_fully_labelled():
    ids = [d["id"] for d in DOCS]
    assert len(ids) == len(set(ids)) == 22
    for d in DOCS:
        t = d["truth"]
        assert {"category", "amount_inr", "due_date", "consequence_keywords", "scam_level", "scam_signs"} <= set(t)
        assert "SPECIMEN" in d["html"] or "नमूना" in d["html"]
    scams = [d for d in DOCS if d["truth"]["scam_level"] == ["warning"]]
    assert len(scams) == 6 and all(d["truth"]["scam_signs"] for d in scams)
