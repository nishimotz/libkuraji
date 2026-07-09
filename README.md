# libkuraji

日本語点訳エンジン（NVDA 日本語版由来）/ Japanese Braille translator originally developed for NVDAJP.

漢字仮名交じりの日本語テキストを、形態素解析による分かち書き（マスあけ）とともに日本語 6 点点字（Unicode braille patterns）へ変換します。点字セルごとの元テキスト位置マップも返します。

## 必要要件

- Python 3.10 以上
- `pip install libkuraji[integration]`（`fugashi`）
- 環境変数 `LIBKURAJI_INTEGRATION=1`（JTalk 拡張辞書の利用を有効化）

## インストール

```console
pip install 'git+https://github.com/nishimotz/libkuraji.git[integration]'
export LIBKURAJI_INTEGRATION=1   # Windows PowerShell: $env:LIBKURAJI_INTEGRATION=1
```

macOS や Homebrew 版 Python では、システム全体へのインストールが制限されることがあります。その場合は仮想環境を使ってください。

```console
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install 'git+https://github.com/nishimotz/libkuraji.git[integration]'
export LIBKURAJI_INTEGRATION=1
```

### 開発向け（リポジトリから）

```console
git clone https://github.com/nishimotz/libkuraji.git
cd libkuraji
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,integration]'
export LIBKURAJI_INTEGRATION=1
```

zsh では `[dev]` や `[integration]` をクォートしてください（`'.[dev,integration]'`）。

## クイックスタート

初回実行時に [libkuraji-jtalk-dic](https://github.com/nishimotz/libkuraji-jtalk-dic) の辞書バイナリが GitHub Release から自動ダウンロードされます。

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

`unicodeIO=True` を指定してください（CLI と同じ Unicode 点字が返ります）。

## 使い方

### Python API

```python
import libkuraji

cells, inpos, outpos, cursor = libkuraji.translate_kanji(
    "私は点字を読みます。",
    unicodeIO=True,
)
# cells[i] に対応する入力位置が inpos[i]
# 入力位置 j に対応する点字位置が outpos[j]
```

カスタムの形態素解析器を使う場合は、`initialize` で注入できます。解析器は `analyze(text, logwrite)` と `is_ready()` を実装している必要があります。

```python
libkuraji.initialize(analyzer=my_analyzer)
cells, inpos, outpos, cursor = libkuraji.translate_kanji(
    "私は点字を読みます。",
    unicodeIO=True,
)
```

NABCC（コンピュータ点字）モードは `translate_kanji(text, nabcc=True, unicodeIO=True)`。

出力の文字コード仕様（Unicode 点字 / liblouis dotsIO、`unicodeIO` の意味）は [docs/encoding.md](docs/encoding.md) にまとめています。

#### MeCab のセットアップ

| 環境 | 備考 |
|------|------|
| Windows | `fugashi` の wheel に `libmecab.dll` が同梱されるため、`pip` だけで動作します |
| macOS / Linux | 本リポジトリの検証では `fugashi` のみで動作しました。環境によっては [MeCab](https://taku910.github.io/mecab/) のシステムインストールが必要な場合があります |

辞書の取得先タグは `LIBKURAJI_JTALK_DIC_TAG` で上書きできます（既定値は `src/libkuraji/jtalk_dic.py` の `DEFAULT_DIC_TAG`）。展開済み辞書ディレクトリを直接指定する場合は `LIBKURAJI_JTALK_DIC_DIR` を使えます（ダウンロードをスキップします）。

### CLI

```console
kuraji "私は点字を読みます。"
⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲

kuraji "私は点字を読みます。" --positions
{"text": "私は点字を読みます。", "braille": "⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲", ...}
```

主なオプション:

| オプション | 説明 |
|-----------|------|
| `-p` / `--positions` | 位置マップを JSON で出力 |
| `--nabcc` | NABCC（コンピュータ点字）モード |
| `-j` / `--kanji` | 漢字交じりモードを強制 |
| `-k` / `--kana` | カナ専用モード（後述） |

### カナ入力のみ（補足）

すでにカナ表記のテキストを点訳する場合は、MeCab なしで `translate` を使えます。

```python
from libkuraji import translate

translate("ワタシワ テンジヲ ヨミマス。")
```

```console
kuraji -k "ワタシワ テンジヲ ヨミマス。"
```

## テスト

### 通常テスト（CI と同じ）

MeCab なしで実行できます。`tests/mecabFixture.json` に録画した MeCab 出力を再生して translator2 を検証します。

```console
pip install -e '.[dev]'
pytest
```

テストデータ `tests/harness.json` 等は点訳のてびきの規則に基づくテストケース集です。`tests/mecabFixture.json` の再録画は nvdajp リポジトリの `miscDepsJp/jptools/recordMecabFixture.py` を使います。

### 実辞書を使った統合テスト（任意）

実際の JTalk 拡張辞書と MeCab で点訳を検証する opt-in テストです。

事前要件:

- `pip install -e '.[dev,integration]'`
- `gh` CLI（未導入なら GitHub REST API にフォールバック）

実行:

```console
export LIBKURAJI_INTEGRATION=1
pytest tests/test_integration.py -q

# MeCab 出力の完全一致チェック（パリティテスト）も実行する場合
export LIBKURAJI_PARITY_CHECK=1
pytest tests/test_integration.py -q
```

Windows PowerShell の場合:

```powershell
$env:LIBKURAJI_INTEGRATION=1
pytest tests/test_integration.py -q
```

統合テストの一部は CI（GitHub Actions）の Windows および Linux 環境でも自動実行されます。`test_mecab_fixture_parity`（MeCab 本体のバージョン差による内部出力の比較）は辞書アップデート時の差分検証用のため、デフォルトではスキップされます。

統合テストは `mecab_correct.py`（元 nvdajp の `Mecab_correctFeatures` を BSD 再許諾のうえ移管）で MeCab 出力の補正も再現しています。`fugashi` 同梱の `libmecab.dll` と fixture 録画時の nvdajp 版 MeCab では、記号のみの入力など少数ケースで内部出力が一致しないことがあります（全体の約 98% は一致）。点訳の最終出力の整合性は維持されており、CI も Green でパスする構成です。

## NVDA 日本語版との関係

- 本ライブラリは [nvdajp](https://github.com/nvdajp/nvdajp) の点訳エンジン（translator1/translator2）を分離・独立させたものです。translator1 相当（`kana` モジュール）はテスト駆動で新規に書き直したクリーンルーム実装、translator2 は著作権者による BSD 再許諾のうえ移管しました。
- 分離計画の詳細: nvdajp の `projectDocs/jp/braille-engine-decoupling-plan.md`

## ライセンス

BSD 3-Clause License. See [LICENSE](LICENSE).
