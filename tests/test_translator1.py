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
        case_id = "%s-%d" % (filename.split(".")[0], idx)
        marks = []
        if t.get("mode", mode_default) == "NABCC":
            marks.append(pytest.mark.skip(reason="NABCC mode not implemented yet"))
        cases.append(pytest.param(t, id=case_id, marks=marks))
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
