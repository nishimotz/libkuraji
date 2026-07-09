import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from libkuraji import translate, translate_kanji
from libkuraji.cli import main
from libkuraji.jtalk_dic import (
    _parse_sha256_digest,
    _safe_extract_zip,
    _validate_dic_tag,
    _verify_zip_sha256,
    download_dic,
)
from libkuraji.limits import InputTooLongError, enforce_max_input_length


def test_validate_dic_tag_accepts_semver_tags():
    assert _validate_dic_tag("v1.1.4") == "v1.1.4"


@pytest.mark.parametrize(
    "tag",
    [
        "../evil",
        "v1.1.4/extra",
        "v1.1",
        "1.1.4",
        "",
    ],
)
def test_validate_dic_tag_rejects_unsafe_values(tag):
    with pytest.raises(ValueError, match="invalid dictionary release tag"):
        _validate_dic_tag(tag)


def test_parse_sha256_digest():
    content = "abc123  jtalk-dic-v1.1.4.zip\n"
    assert _parse_sha256_digest(content) == "abc123"


def test_verify_zip_sha256(tmp_path):
    data = b"zip payload"
    zip_path = tmp_path / "sample.zip"
    zip_path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    _verify_zip_sha256(zip_path, digest)

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        _verify_zip_sha256(zip_path, "0" * 64)


def test_safe_extract_zip_rejects_traversal(tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../evil.txt", "boom")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
        with pytest.raises(RuntimeError, match="unsafe zip member path"):
            _safe_extract_zip(zf, dest)


def test_safe_extract_zip_allows_normal_members(tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sys.dic", "dummy")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
        _safe_extract_zip(zf, dest)
    assert (dest / "sys.dic").read_text(encoding="utf-8") == "dummy"


def test_download_dic_verifies_sha256_before_extract(tmp_path, monkeypatch):
    tag = "v9.9.9"
    monkeypatch.setenv("LIBKURAJI_CACHE_DIR", str(tmp_path / "cache"))

    cache = tmp_path / "cache" / "libkuraji-jtalk-dic"
    zip_name = f"jtalk-dic-{tag}.zip"
    sha_name = f"jtalk-dic-{tag}.zip.sha256"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("sys.dic", "dummy")
    good_zip = buf.getvalue()
    good_digest = hashlib.sha256(good_zip).hexdigest()

    def fake_download(tag_arg, asset_name, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        if asset_name == zip_name:
            dest.write_bytes(good_zip)
        elif asset_name == sha_name:
            dest.write_text(f"{good_digest}  {zip_name}\n", encoding="utf-8")
        else:
            raise AssertionError(asset_name)

    monkeypatch.setattr("libkuraji.jtalk_dic._download_asset_via_rest", fake_download)

    extracted = download_dic(tag)
    assert extracted.name == tag
    assert (extracted / "sys.dic").exists()


def test_enforce_max_input_length(monkeypatch):
    monkeypatch.setenv("LIBKURAJI_MAX_INPUT_CHARS", "3")
    enforce_max_input_length("abc")
    with pytest.raises(InputTooLongError):
        enforce_max_input_length("abcd")


def test_translate_rejects_overlong_input(monkeypatch):
    monkeypatch.setenv("LIBKURAJI_MAX_INPUT_CHARS", "1")
    with pytest.raises(InputTooLongError):
        translate("アイ")


def test_translate_kanji_rejects_overlong_input(monkeypatch):
    monkeypatch.setenv("LIBKURAJI_MAX_INPUT_CHARS", "1")
    analyzer = type(
        "Analyzer",
        (),
        {
            "is_ready": lambda self: True,
            "analyze": lambda self, text, logwrite=None: [],
        },
    )()
    import libkuraji

    libkuraji.initialize(analyzer)
    try:
        with pytest.raises(InputTooLongError):
            translate_kanji("私は", unicodeIO=True)
    finally:
        libkuraji.terminate()


def test_cli_reports_overlong_input(capsys, monkeypatch):
    monkeypatch.setenv("LIBKURAJI_MAX_INPUT_CHARS", "1")
    code = main(["--kana", "アイ"])
    captured = capsys.readouterr()
    assert code == 1
    assert "exceeds limit" in captured.err
