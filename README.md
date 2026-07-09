# libkuraji

[日本語](README-ja.md)

Japanese Braille translator originally developed for NVDAJP.

Translates mixed Kanji/Kana Japanese text into Japanese 6-dot braille (Unicode braille patterns), with morphological word segmentation (masuake / spacing). Returns a position map from each braille cell back to the source text.

## Requirements

- Python 3.10 or later
- `pip install libkuraji[integration]` (`fugashi`)
- Environment variable `LIBKURAJI_INTEGRATION=1` (enables the JTalk extended dictionary)

## Installation

```console
pip install 'git+https://github.com/nishimotz/libkuraji.git[integration]'
export LIBKURAJI_INTEGRATION=1   # Windows PowerShell: $env:LIBKURAJI_INTEGRATION=1
```

On macOS and Homebrew Python, system-wide installs may be restricted. Use a virtual environment in that case.

```console
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install 'git+https://github.com/nishimotz/libkuraji.git[integration]'
export LIBKURAJI_INTEGRATION=1
```

### For development (from the repository)

```console
git clone https://github.com/nishimotz/libkuraji.git
cd libkuraji
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,integration]'
export LIBKURAJI_INTEGRATION=1
```

In zsh, quote the extras: `'.[dev,integration]'`.

## Quick start

On first run, dictionary binaries from [libkuraji-jtalk-dic](https://github.com/nishimotz/libkuraji-jtalk-dic) are downloaded automatically from GitHub Releases.

```console
kuraji "私は点字を読みます。"
# => ⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲
```

```python
import libkuraji

cells, inpos, outpos, cursor = libkuraji.translate_kanji(
    "私は点字を読みます。",
    unicodeIO=True,
)
# => '⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲'
```

Pass `unicodeIO=True` to get Unicode braille (the same format as the CLI).

Input is limited to 65,536 characters by default (`InputTooLongError` when exceeded). Override with `LIBKURAJI_MAX_INPUT_CHARS`; set `0` to disable the limit.

## Usage

### Python API

```python
import libkuraji

cells, inpos, outpos, cursor = libkuraji.translate_kanji(
    "私は点字を読みます。",
    unicodeIO=True,
)
# inpos[i] is the input index for cells[i]
# outpos[j] is the braille index for input position j
```

To use a custom morphological analyzer, inject it with `initialize`. The analyzer must implement `analyze(text, logwrite)` and `is_ready()`.

```python
libkuraji.initialize(analyzer=my_analyzer)
cells, inpos, outpos, cursor = libkuraji.translate_kanji(
    "私は点字を読みます。",
    unicodeIO=True,
)
```

For NABCC (computer braille) mode: `translate_kanji(text, nabcc=True, unicodeIO=True)`.

See [docs/encoding.md](docs/encoding.md) for output encoding details (Unicode braille vs liblouis dotsIO, and what `unicodeIO` means).

#### MeCab setup

| Platform | Notes |
|----------|-------|
| Windows | The `fugashi` wheel bundles `libmecab.dll`, so `pip` alone is sufficient |
| macOS / Linux | Verified in this repository with `fugashi` only. Some environments may require a system [MeCab](https://taku910.github.io/mecab/) install |

Override the dictionary release tag with `LIBKURAJI_JTALK_DIC_TAG` (default: `DEFAULT_DIC_TAG` in `src/libkuraji/jtalk_dic.py`). To skip download, point `LIBKURAJI_JTALK_DIC_DIR` at an already extracted dictionary directory.

### CLI

```console
kuraji "私は点字を読みます。"
⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲

kuraji "私は点字を読みます。" --positions
{"text": "私は点字を読みます。", "braille": "⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲", ...}
```

Main options:

| Option | Description |
|--------|-------------|
| `-p` / `--positions` | Output position map as JSON |
| `--nabcc` | NABCC (computer braille) mode |
| `-j` / `--kanji` | Force mixed Kanji/Kana mode |
| `-k` / `--kana` | Kana-only mode (see below) |

### Kana input only (supplement)

If the input is already in katakana, use `translate` without MeCab.

```python
from libkuraji import translate

translate("ワタシワ テンジヲ ヨミマス。")
```

```console
kuraji -k "ワタシワ テンジヲ ヨミマス。"
```

## Testing

### Default tests (same as CI)

Runs without MeCab. Replays recorded MeCab output from `tests/mecabFixture.json` to verify translator2.

```console
pip install -e '.[dev]'
pytest
```

Test data in `tests/harness.json` and related files follow rules from the Japanese braille guide (*Ten'yaku no Tebiki*). To re-record `tests/mecabFixture.json`, use `miscDepsJp/jptools/recordMecabFixture.py` in the nvdajp repository.

### Integration tests with the real dictionary (optional)

Opt-in tests that verify translation against the live JTalk extended dictionary and MeCab.

Prerequisites:

- `pip install -e '.[dev,integration]'`
- `gh` CLI (falls back to the GitHub REST API if unavailable)

Run:

```console
export LIBKURAJI_INTEGRATION=1
pytest tests/test_integration.py -q

# Also run exact MeCab output parity checks
export LIBKURAJI_PARITY_CHECK=1
pytest tests/test_integration.py -q
```

On Windows PowerShell:

```powershell
$env:LIBKURAJI_INTEGRATION=1
pytest tests/test_integration.py -q
```

Some integration tests also run in CI (GitHub Actions) on Windows and Linux. `test_mecab_fixture_parity` (internal MeCab output comparison across versions) is skipped by default and intended for dictionary update verification.

Integration tests also reproduce MeCab output correction via `mecab_correct.py` (ported from nvdajp's `Mecab_correctFeatures` under BSD relicensing). The `libmecab.dll` bundled with `fugashi` and the nvdajp MeCab used when recording fixtures may differ on a few symbol-only inputs (about 98% match overall). Final braille output consistency is preserved and CI passes.

## Relationship to NVDA Japanese

- This library separates and standalone-izes the braille engine (translator1/translator2) from [nvdajp](https://github.com/nvdajp/nvdajp). The translator1 equivalent (`kana` module) is a clean-room rewrite driven by tests; translator2 was ported under BSD relicensing by the copyright holder.
- Decoupling plan: `projectDocs/jp/braille-engine-decoupling-plan.md` in the nvdajp repository.

## License

BSD 3-Clause License. See [LICENSE](LICENSE).
