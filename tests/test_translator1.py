# Tests for the kana-to-braille stage against the harness test data.
# Copyright (C) 2026 Takuya Nishimoto
# License: BSD 3-Clause. See LICENSE.

import json
from pathlib import Path

import pytest

from libkuraji.kana import translate_with_pos

_TESTS_DIR = Path(__file__).parent


def _load_cases(filename, mode_default=""):
    data = json.loads((_TESTS_DIR / filename).read_text(encoding="utf-8"))
    cases = []
    for idx, t in enumerate(data):
        if "input" not in t or "output" not in t:
            continue
        t.setdefault("mode", mode_default)
        cases.append(pytest.param(t, id="%s-%d" % (filename.split(".")[0], idx)))
    return cases


_CASES = _load_cases("harness.json") + _load_cases("nabccHarness.json", "NABCC")


@pytest.mark.parametrize("case", _CASES)
def test_kana_to_braille(case):
    nabcc = case.get("mode") == "NABCC"
    result, inpos = translate_with_pos(case["input"], nabcc=nabcc)
    assert result == case["output"]
    assert len(result) == len(inpos)
    if "inpos1" in case:
        assert inpos == case["inpos1"]


def test_underscore_translation():
    # Single underscore: dot 5, dots 3-6 (⠐⠤)
    cells, inpos = translate_with_pos("_")
    assert cells == "⠐⠤"
    assert inpos == [0, 0]

    # Underscore in uppercase identifier
    cells, inpos = translate_with_pos("A_B")
    assert cells == "⠰⠠⠁⠐⠤⠰⠠⠃"
    assert inpos == [0, 0, 0, 1, 1, 2, 2, 2]

    # Underscore in lowercase identifier
    cells, inpos = translate_with_pos("a_b")
    assert cells == "⠰⠁⠐⠤⠰⠃"
    assert inpos == [0, 0, 1, 1, 2, 2]

    # Underscore between kana words
    cells, inpos = translate_with_pos("テスト_テスト")
    assert "⠐⠤" in cells


def test_readmejp_symbols():
    # readmejp.md: |$ 半角ドル |56-1456 |⠰⠹|
    cells, inpos = translate_with_pos("$")
    assert cells == "⠰⠹"
    assert inpos == [0, 0]

    # readmejp.md: || 縦棒 |2356 |⠶|
    cells, inpos = translate_with_pos("|")
    assert cells == "⠶"
    assert inpos == [0]

    # fullwidth vertical bar ｜
    cells, inpos = translate_with_pos("｜")
    assert cells == "⠶"
    assert inpos == [0]

    # readmejp.md: |; 半角セミコロン |23 |⠆|
    cells, inpos = translate_with_pos(";")
    assert cells == "⠆"
    assert inpos == [0]

    # readmejp.md: |\ 半角円 |16 |⠡|
    cells, inpos = translate_with_pos("\\")
    assert cells == "⠡"
    assert inpos == [0]

