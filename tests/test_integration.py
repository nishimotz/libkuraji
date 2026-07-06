# Integration tests against the real MeCab + JTalk extended dictionary.
# Copyright (C) 2026 Takuya Nishimoto
# License: BSD 3-Clause. See LICENSE.
#
# These tests are OPT-IN. They are skipped unless:
#   - LIBKURAJI_INTEGRATION=1 is set, AND
#   - fugashi is importable (pip install -e .[integration]), AND
#   - the MeCab runtime (libmecab) is available on the system.
#
# When enabled, the JTalk dictionary binaries are fetched from the
# libkuraji-jtalk-dic GitHub Release (pinned tag, overridable via
# LIBKURAJI_JTALK_DIC_TAG) and cached locally.
#
# The default CI workflow does NOT set LIBKURAJI_INTEGRATION, so these
# tests stay skipped there; the replay-based tests in test_translator1.py
# and test_translator2.py remain the source of truth for CI.
#
# Run locally with:
#   pip install -e .[integration]
#   $env:LIBKURAJI_INTEGRATION=1
#   pytest tests/test_integration.py -q

import json
import os
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).parent


def _integration_enabled() -> bool:
    return os.environ.get("LIBKURAJI_INTEGRATION", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


# Skip the whole module unless explicitly opted in. fugashi is imported
# lazily inside the fixture so that missing dependencies don't break
# collection of the rest of the suite.
pytestmark = pytest.mark.skipif(
    not _integration_enabled(),
    reason="set LIBKURAJI_INTEGRATION=1 to run dictionary integration tests",
)


def _load(filename):
    return json.loads((_TESTS_DIR / filename).read_text(encoding="utf-8"))


def _load_cases(filename, mode_default=""):
    cases = []
    for idx, t in enumerate(_load(filename)):
        if "input" not in t or "output" not in t:
            continue
        t.setdefault("mode", mode_default)
        cases.append(pytest.param(t, id="%s-%d" % (filename.split(".")[0], idx)))
    return cases


def _separation_cases():
    cases = []
    for filename, default_mode in (
        ("harness.json", ""),
        ("nabccHarness.json", "NABCC"),
    ):
        for idx, t in enumerate(_load(filename)):
            if "text" not in t or "input" not in t:
                continue
            t.setdefault("mode", default_mode)
            cases.append(pytest.param(t, id="%s-%d" % (filename.split(".")[0], idx)))
    return cases


def _eng2_cases():
    cases = []
    for idx, t in enumerate(_load("eng2Harness.json")):
        if "text" not in t or "output" not in t:
            continue
        if "_output" in t:  # known-failure convention: skip
            continue
        cases.append(pytest.param(t, id="eng2Harness-%d" % idx))
    return cases


_LOG = lambda s: None  # noqa: E731


@pytest.fixture(scope="module")
def analyzer():
    from libkuraji.jtalk_dic import make_analyzer
    return make_analyzer(logwrite=_LOG)


@pytest.fixture(scope="module", autouse=True)
def _initialized(analyzer):
    from libkuraji import translator2
    translator2.initialize(analyzer=analyzer, logwrite=_LOG)
    yield
    translator2.terminate()


# --- stage 1 (kana -> braille) does NOT need the analyzer; but reuse the
#     same opt-in gate to keep these "real dictionary" runs grouped. ---
_CASES_KANA = _load_cases("harness.json") + _load_cases("nabccHarness.json", "NABCC")


@pytest.mark.parametrize("case", _CASES_KANA)
def test_kana_to_braille(case):
    from libkuraji.kana import translate_with_pos
    nabcc = case.get("mode") == "NABCC"
    result, inpos = translate_with_pos(case["input"], nabcc=nabcc)
    assert result == case["output"]
    assert len(result) == len(inpos)
    if "inpos1" in case:
        assert inpos == case["inpos1"]


@pytest.mark.parametrize("case", _separation_cases())
def test_word_separation(case):
    from libkuraji import translator2
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


@pytest.mark.parametrize("case", _eng2_cases())
def test_eng2_grade1(case):
    from libkuraji import translator2
    _, braille, _, _ = translator2.translateWithInPos2(
        case["text"], logwrite=_LOG, nabcc=False, use_foreign_quotes=True
    )
    assert braille == case["output"]


# --- fixture parity check -------------------------------------------------
# mecabFixture.json records the MeCab output the replay tests rely on.
# When running against the real dictionary we can check that the recorded
# analysis still matches what the current dictionary produces, surfacing
# dictionary drift early.
_FIXTURE = _load("mecabFixture.json")


def _fixture_parity_cases():
    cases = []
    for text, expected in _FIXTURE.items():
        cases.append(pytest.param((text, expected), id="fixture-%d" % len(cases)))
    return cases


@pytest.mark.parametrize("text_expected", _fixture_parity_cases())
def test_mecab_fixture_parity(text_expected, analyzer):
    text, expected = text_expected
    got = analyzer.analyze(text, logwrite=_LOG)
    assert got == expected, (
        f"MeCab output for {text!r} drifted from mecabFixture.json; "
        f"re-record the fixture if the dictionary intentionally changed."
    )