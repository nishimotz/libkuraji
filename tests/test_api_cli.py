import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import libkuraji
from libkuraji import translator2
from libkuraji.cli import main

_TESTS_DIR = Path(__file__).parent
_FIXTURE = json.loads((_TESTS_DIR / "mecabFixture.json").read_text(encoding="utf-8"))


class ReplayAnalyzer:
    def __init__(self, recorded):
        self._recorded = recorded

    def is_ready(self):
        return True

    def analyze(self, text, logwrite=None):
        try:
            return self._recorded[text]
        except KeyError:
            raise KeyError("no recorded analysis for %r" % text)


def test_public_api():
    # Setup custom analyzer
    analyzer = ReplayAnalyzer(_FIXTURE)
    libkuraji.initialize(analyzer)

    # Test translate_kanji
    text = "アドレスはabc.123.jpです。"
    braille, in_pos, out_pos, cursor = libkuraji.translate_kanji(text, unicodeIO=True)
    assert braille == "⠁⠐⠞⠛⠹⠄ ⠦⠁⠃⠉⠲⠼⠁⠃⠉⠲⠚⠏⠴ ⠐⠟⠹⠲"
    assert len(in_pos) == len(braille)

    # Test terminate
    libkuraji.terminate()
    assert not translator2.mecab_initialized


def test_cli_kana(capsys):
    # Test standard kana translation via CLI
    code = main(["--kana", "ア"])
    assert code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "⠁"


def test_cli_positions(capsys):
    # Test positions JSON output
    code = main(["--kana", "--positions", "ア"])
    assert code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["text"] == "ア"
    assert data["braille"] == "⠁"
    assert data["inPos"] == [0]
    assert data["outPos"] == [0]


def test_cli_kanji_with_replay(capsys):
    # Test kanji translation via CLI when analyzer is initialized
    analyzer = ReplayAnalyzer(_FIXTURE)
    libkuraji.initialize(analyzer)

    try:
        code = main(["-j", "アドレスはabc.123.jpです。"])
        assert code == 0
        captured = capsys.readouterr()
        assert captured.out.strip() == "⠁⠐⠞⠛⠹⠄ ⠦⠁⠃⠉⠲⠼⠁⠃⠉⠲⠚⠏⠴ ⠐⠟⠹⠲"
    finally:
        libkuraji.terminate()


def test_cli_kanji_no_mecab_error(capsys):
    # Test CLI error when MeCab is requested but not installed
    with patch.dict("sys.modules", {"fugashi": None}):
        code = main(["-j", "漢字"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Error: Mixed-text translation requires MeCab" in captured.err

        # Test auto-detection error
        code = main(["漢字"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Error: Input contains Kanji but MeCab is not installed" in captured.err
