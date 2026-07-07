# coding: UTF-8
# jtalk_dic.py
# Copyright (C) 2026 Takuya Nishimoto
# License: BSD 3-Clause. See LICENSE.
#
# MeCab + JTalk extended dictionary (NAIST-JDIC + nvdajp custom entries)
# adapter for translator2.
#
# The dictionary binaries (sys.dic, matrix.bin, char.bin, unk.dic, dicrc,
# DIC_VERSION) are NOT part of this source tree. They are built and published
# from the libkuraji-jtalk-dic repository as GitHub Release assets
# (jtalk-dic-v*.zip). This module downloads the zip for a pinned tag on
# demand, extracts it to a cache directory, and wraps a fugashi Tagger so it
# can be injected into translator2.initialize(analyzer=...).
#
# This is an OPTIONAL runtime path. The default libkuraji test suite uses
# a recorded fixture (mecabFixture.json) via ReplayAnalyzer and does not
# require MeCab, fugashi, or network access. Integration tests opt in via
# the LIBKURAJI_INTEGRATION=1 environment variable.

import os
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Callable, List, Optional

# Pinned default release tag of libkuraji-jtalk-dic. Override with the
# LIBKURAJI_JTALK_DIC_TAG environment variable. Bump this when a new
# dictionary release is validated against the harness.
DEFAULT_DIC_TAG = "v1.0.4"

# Owner/repo of the dictionary release.
DIC_REPO = "nishimotz/libkuraji-jtalk-dic"

# Asset name pattern for the dictionary zip. Must match release-dic.yml
# in libkuraji-jtalk-dic.
_DIC_ZIP_NAME = "jtalk-dic-{tag}.zip"
_DIC_ZIP_SHA_NAME = "jtalk-dic-{tag}.zip.sha256"


# Halfwidth-to-fullwidth conversion for the MeCab input pipeline.
#
# The JTalk extended dictionary (NAIST-JDIC + nvdajp custom entries) was
# built with fullwidth ASCII characters as its unknown-word (unk) class
# definitions, so MeCab must be fed fullwidth input to reproduce the
# analysis recorded in tests/mecabFixture.json. This is the text2mecab
# conversion originally written by Takuya Nishimoto for python-jtalk,
# re-licensed to BSD 3-Clause for libkuraji.
#
# The dedicated fullwidth block U+FF01..U+FF5E mirrors ASCII U+0021..U+007E
# one-to-one. The ASCII space (U+0020) maps to U+3000. Three characters
# have special targets that differ from the naive fullwidth mapping:
# - "-" (HYPHEN-MINUS) -> U+2212 MINUS SIGN
# - "~" (TILDE) -> U+301C WAVE DASH
# - "\" (REVERSE SOLIDUS) -> U+FFE5 FULLWIDTH YEN SIGN
# - U+FFFD REPLACEMENT CHARACTER -> fullwidth question mark
_HALF_TO_FULL: dict[str, str] = {}
for _c in range(0x21, 0x7F):  # '!' .. '~'
    _HALF_TO_FULL[chr(_c)] = chr(_c + 0xFEE0)
_HALF_TO_FULL[" "] = "\u3000"  # fullwidth space
_HALF_TO_FULL["-"] = "\u2212"  # MINUS SIGN
_HALF_TO_FULL["~"] = "\u301C"  # WAVE DASH
_HALF_TO_FULL["\\"] = "\uFFE5"  # FULLWIDTH YEN SIGN
_HALF_TO_FULL["\ufffd"] = "\uff1f"  # fullwidth question mark
_HALF2FULL_TABLE = str.maketrans(_HALF_TO_FULL)


def _to_mecab_text(text: str) -> str:
    """Normalize text the way the JTalk dictionary expects.

    NFKC-normalize (which folds compatibility characters down to their
    halfwidth ASCII form), then widen ASCII to the fullwidth block the
    dictionary's unk classes were built against.
    """
    text = unicodedata.normalize("NFKC", text)
    return text.translate(_HALF2FULL_TABLE)


def _env_truthy(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def get_dic_tag() -> str:
    """Return the dictionary release tag to use."""
    return os.environ.get("LIBKURAJI_JTALK_DIC_TAG", DEFAULT_DIC_TAG).strip() or DEFAULT_DIC_TAG


def get_cache_dir() -> Path:
    """Return the cache directory used to store downloaded dictionaries.

    Override with LIBKURAJI_JTALK_DIC_DIR (points directly at an already
    extracted dictionary directory, skipping download entirely).
    """
    override = os.environ.get("LIBKURAJI_JTALK_DIC_DIR", "").strip()
    if override:
        return Path(override)
    base = os.environ.get("LIBKURAJI_CACHE_DIR", "").strip()
    if base:
        return Path(base) / "libkuraji-jtalk-dic"
    # ~/.cache/libkuraji-jtalk-dic on POSIX, %LOCALAPPDATA% on Windows.
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "libkuraji-jtalk-dic"
    return Path.home() / ".cache" / "libkuraji-jtalk-dic"


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def download_dic(tag: Optional[str] = None, force: bool = False) -> Path:
    """Download and extract the dictionary zip for the given release tag.

    Returns the path to the extracted dictionary directory (the one
    containing sys.dic). Uses the gh CLI if available, otherwise falls
    back to the GitHub REST API via urllib.
    """
    tag = tag or get_dic_tag()
    cache = get_cache_dir()
    # When LIBKURAJI_JTALK_DIC_DIR points directly at a dictionary dir,
    # cache == that dir and we must not try to "extract" into it.
    if os.environ.get("LIBKURAJI_JTALK_DIC_DIR", "").strip():
        if (cache / "sys.dic").exists():
            return cache
        raise FileNotFoundError(
            f"LIBKURAJI_JTALK_DIC_DIR={cache} does not contain sys.dic"
        )

    extracted = cache / tag
    if (extracted / "sys.dic").exists() and not force:
        return extracted

    cache.mkdir(parents=True, exist_ok=True)
    zip_name = _DIC_ZIP_NAME.format(tag=tag)
    zip_path = cache / zip_name

    if not zip_path.exists() or force:
        downloaded = False
        if _gh_available():
            try:
                subprocess.run(
                    [
                        "gh", "release", "download", tag,
                        "--repo", DIC_REPO,
                        "--pattern", zip_name,
                        "--dir", str(cache),
                        "--clobber",
                    ],
                    check=True,
                    capture_output=True,
                )
                downloaded = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        if not downloaded:
            _download_via_rest(tag, zip_name, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extracted)

    dicrc_path = extracted / "dicrc"
    if dicrc_path.exists():
        try:
            content = dicrc_path.read_bytes()
            lf_content = content.replace(b"\r\n", b"\n")
            if lf_content != content:
                dicrc_path.write_bytes(lf_content)
        except Exception:
            pass

    if not (extracted / "sys.dic").exists():
        raise RuntimeError(
            f"sys.dic not found in extracted {zip_name}; archive layout changed?"
        )
    return extracted


def _download_via_rest(tag: str, asset_name: str, dest: Path) -> None:
    import urllib.request
    import json

    url = f"https://api.github.com/repos/{DIC_REPO}/releases/tags/{tag}"
    with urllib.request.urlopen(url) as r:  # noqa: S310 - trusted public endpoint
        release = json.loads(r.read().decode("utf-8"))
    asset_url = None
    for a in release.get("assets", []):
        if a.get("name") == asset_name:
            asset_url = a.get("browser_download_url")
            break
    if not asset_url:
        raise RuntimeError(f"asset {asset_name} not found in release {tag}")
    with urllib.request.urlopen(asset_url) as r, dest.open("wb") as f:  # noqa: S310
        shutil.copyfileobj(r, f)


class JTalkDicAnalyzer:
    """Morphological analyzer backed by MeCab (via fugashi) and the
    JTalk extended dictionary.

    Implements the small contract expected by translator2.initialize():
    - is_ready() -> bool
    - analyze(text, logwrite=None) -> list[str]   (MeCab feature lines)

    The feature lines are returned in the CSV form translator2 expects
    (surface + 13+ comma-separated feature fields), matching the format
    emitted by the JTalk extended dictionary's braille-notation field.
    """

    def __init__(self, dic_dir: Path, logwrite: Optional[Callable[[str], None]] = None):
        self.dic_dir = Path(dic_dir)
        self._log = logwrite or (lambda s: None)
        self._tagger = None
        try:
            from fugashi import GenericTagger  # type: ignore
        except ImportError as e:
            raise ImportError(
                "fugashi is required for JTalkDicAnalyzer; "
                "install with `pip install -e .[integration]`"
            ) from e
        # fugashi.Tagger (the Unidic variant) rejects dictionaries whose
        # feature field count doesn't match Unidic's schema, so we use the
        # GenericTagger which accepts any feature layout.
        #
        # fugashi wraps the user arg with a forced `-C` and runs it through
        # shlex.split, which mangles backslashes on Windows. Always pass
        # forward-slash paths, and give MeCab an explicit `-r <dicrc>` so it
        # doesn't fall back to the system default (`c:\mecab\mecabrc`).
        d = str(self.dic_dir).replace("\\", "/")
        arg = f"-r {d}/dicrc -d {d}"
        self._tagger = GenericTagger(arg)
        self._log(f"JTalkDicAnalyzer initialized with dic_dir={self.dic_dir}")

    def is_ready(self) -> bool:
        return self._tagger is not None and (self.dic_dir / "sys.dic").exists()

    def _reparse(self, text: str) -> List[str]:
        """Re-parse a single character to fill missing readings.

        Used by correct_features (PATTERN 1/2) for unknown words whose
        reading is empty. The input is widened the same way as analyze().
        """
        text = _to_mecab_text(text)
        out: list[str] = []
        for word in self._tagger(text):
            out.append(f"{word.surface},{word.feature_raw}")
        return out

    def analyze(self, text: str, logwrite: Optional[Callable[[str], None]] = None) -> List[str]:
        if self._tagger is None:
            raise RuntimeError("JTalkDicAnalyzer: tagger not initialized")
        log = logwrite or self._log
        # The JTalk dictionary's unknown-word classes are defined for
        # fullwidth ASCII, so we widen the input before handing it to
        # MeCab. This matches the analysis recorded in mecabFixture.json.
        text = _to_mecab_text(text)
        # GenericTagger exposes `feature_raw` (CSV feature string) and
        # `surface`. translator2.mecab_to_morphs expects each line to start
        # with the surface, followed by the comma-separated feature fields,
        # matching the format recorded in mecabFixture.json.
        raw_lines: list[str] = []
        for word in self._tagger(text):
            surface = word.surface
            raw = word.feature_raw
            raw_lines.append(f"{surface},{raw}")
            log(f"mecab: {raw_lines[-1]}")
        # Post-process (correct) the features to match the reference
        # analysis. The correction may re-parse individual characters to
        # fill missing readings for unknown words.
        from .mecab_correct import correct_features
        return correct_features(raw_lines, reparse=self._reparse)


def make_analyzer(
    tag: Optional[str] = None,
    logwrite: Optional[Callable[[str], None]] = None,
) -> JTalkDicAnalyzer:
    """Convenience: download (if needed) and return a ready analyzer.

    Requires LIBKURAJI_INTEGRATION=1 to be set; otherwise raises so that
    accidental calls in the default test path fail loudly.
    """
    if not _env_truthy("LIBKURAJI_INTEGRATION"):
        raise RuntimeError(
            "JTalk dictionary integration is opt-in; "
            "set LIBKURAJI_INTEGRATION=1 to enable."
        )
    dic_dir = download_dic(tag)
    return JTalkDicAnalyzer(dic_dir, logwrite=logwrite)