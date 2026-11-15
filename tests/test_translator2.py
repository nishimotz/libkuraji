# Tests for the word-separation stage (translator2) using recorded
# analyzer output, so no MeCab installation is required.
# Copyright (C) 2026 Takuya Nishimoto
# License: BSD 3-Clause. See LICENSE.

import json
from pathlib import Path

import pytest

from libkuraji import translator2

_TESTS_DIR = Path(__file__).parent


class ReplayAnalyzer:
    """Replays MeCab feature lines recorded from the reference
    configuration (JTalk extended dictionary); see mecabFixture.json."""

    def __init__(self, recorded):
        self._recorded = recorded

    def is_ready(self):
        return True

    def analyze(self, text, logwrite=None):
        try:
            return self._recorded[text]
        except KeyError:
            raise KeyError(
                "no recorded analysis for %r; re-record mecabFixture.json" % text
            )


def _load(filename):
    return json.loads((_TESTS_DIR / filename).read_text(encoding="utf-8"))


_FIXTURE = _load("mecabFixture.json")
_LOG = lambda s: None  # noqa: E731


@pytest.fixture(scope="module", autouse=True)
def _initialized():
    translator2.initialize(analyzer=ReplayAnalyzer(_FIXTURE), logwrite=_LOG)


def _separation_cases():
    cases = []
    for filename, default_mode in (("harness.json", ""), ("nabccHarness.json", "NABCC")):
        for idx, t in enumerate(_load(filename)):
            if "text" not in t or "input" not in t:
                continue
            t.setdefault("mode", default_mode)
            cases.append(pytest.param(t, id="%s-%d" % (filename.split(".")[0], idx)))
    return cases


@pytest.mark.parametrize("case", _separation_cases())
def test_word_separation(case):
    nabcc = case.get("mode") == "NABCC"
    result, pat, inpos1, inpos2 = translator2.translateWithInPos2(
        case["text"], logwrite=_LOG, nabcc=nabcc
    )
    assert result == case["input"]
    if "inpos2" in case:
        assert list(inpos2) == case["inpos2"]
    inpos, _ = translator2.mergePositionMap(inpos1, inpos2, len(pat), len(case["text"]))
    if "inpos" in case:
        assert list(inpos) == case["inpos"]
    if "outpos" in case:
        outpos = translator2.makeOutPos(inpos, len(case["text"]), len(pat))
        assert outpos == case["outpos"]


def _eng2_grade1_cases():
    cases = []
    for idx, t in enumerate(_load("eng2Harness.json")):
        if "text" not in t or "output" not in t:
            continue
        if "_output" in t:  # known-failure convention: skip
            continue
        cases.append(pytest.param(t, id="eng2Harness-%d" % idx))
    return cases


@pytest.mark.parametrize("case", _eng2_grade1_cases())
def test_eng2_grade1(case):
    _, braille, _, _ = translator2.translateWithInPos2(
        case["text"], logwrite=_LOG, nabcc=False, use_foreign_quotes=True
    )
    assert braille == case["output"]


def test_bullet_braille_pattern():
    """List bullet (•, U+2022) should map to U+2810 (dot 5) in braille (nvdajp#723)."""
    for text, expected in [
        ("•", "⠐"),
        ("•項目", "⠐ ⠪⠒⠾⠩"),
        ("• 項目", "⠐ ⠪⠒⠾⠩"),
        ("• item", "⠐ ⠰⠊⠞⠑⠍"),
        ("• 1番目", "⠐ ⠼⠁⠐⠥⠴⠿"),
    ]:
        braille, inpos, outpos, cursor = translator2.translate(text, unicodeIO=True)
        assert braille == expected


@pytest.mark.parametrize(
    ("text", "expected_input", "expected_braille"),
    [
        # Decimal cases (nvdajp#778)
        ("年一〇・八％", "トシ 10.8%", "⠞⠳ ⠼⠁⠚⠂⠓⠰⠏"),
        ("〇・五倍", "0.5バイ", "⠼⠚⠂⠑⠐⠥⠃"),
        ("一四・二％", "14.2%", "⠼⠁⠙⠂⠃⠰⠏"),
        ("四七・七％", "47.7%", "⠼⠙⠛⠂⠛⠰⠏"),
        ("二〇・一％", "20.1%", "⠼⠃⠚⠂⠁⠰⠏"),
        ("一三・五％", "13.5%", "⠼⠁⠉⠂⠑⠰⠏"),
        ("一・六％", "1.6%", "⠼⠁⠂⠋⠰⠏"),
        ("〇・八％", "0.8%", "⠼⠚⠂⠓⠰⠏"),
        ("〇・〇八％", "0.08%", "⠼⠚⠂⠚⠓⠰⠏"),
        ("三・〇五％", "3.05%", "⠼⠉⠂⠚⠑⠰⠏"),
        ("三・五割", "3.5ワリ", "⠼⠉⠂⠑⠄⠓"),
        ("一・二五倍", "1.25バイ", "⠼⠁⠂⠃⠑⠐⠥⠃"),
        ("〇・五日", "0.5ニチ", "⠼⠚⠂⠑⠇⠗"),
        ("三・一四", "3.14", "⠼⠉⠂⠁⠙"),
        # Non-decimal / repeated numeric sign cases
        ("七・五・三", "7⠼5⠼3", "⠼⠛⠼⠑⠼⠉"),
        ("六・三・三制", "6⠼3⠼3セイ", "⠼⠋⠼⠉⠼⠉⠻⠃"),
        ("二・二六事件", "2⠼26 ジケン", "⠼⠃⠼⠃⠋ ⠐⠳⠫⠴"),
        ("五・一五事件", "5⠼15 ジケン", "⠼⠑⠼⠁⠑ ⠐⠳⠫⠴"),
        ("二・三日", "2⠼3ニチ", "⠼⠃⠼⠉⠇⠗"),
        ("二・三人", "2⠼3ニン", "⠼⠃⠼⠉⠇⠴"),
    ],
)
def test_kansuji_nakaten_decimal(text, expected_input, expected_braille):
    """Distinguish Kansuji + middle dot decimals from repeated numeric signs (nvdajp#778)."""
    result, pat, _, _ = translator2.translateWithInPos2(text, logwrite=_LOG, nabcc=False)
    assert result == expected_input
    assert pat == expected_braille
