# libkuraji

日本語点訳エンジン（NVDA 日本語版由来）/ Japanese Braille translator originally developed for NVDAJP.

カナ表記のテキストを日本語 6 点点字（Unicode braille patterns）に変換します。形態素解析による分かち書き（マスあけ）と、カナ・記号・英数字の点字化を行い、点字セルごとの元テキスト位置マップを返します。

## インストール

```console
pip install git+https://github.com/nishimotz/libkuraji.git
```

Python 3.10 以上。実行時依存パッケージはありません。

## 使い方

### カナ→点字（translator1 相当）

```python
from libkuraji import translate, translate_with_pos

translate("ワタシワ テンジヲ ヨミマス。")
# => '⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲'

cells, inpos = translate_with_pos("コンニチワ 2026ネン")
# inpos[i] は cells[i] に対応する入力文字のインデックス
```

NABCC（コンピュータ点字）モードは `translate(text, nabcc=True)`。

### 漢字仮名交じり→点字（MeCab / JTalk 拡張辞書）

漢字仮名交じり文をそのまま点訳するには、形態素解析器（MeCab / JTalk 拡張辞書）を使用します。

事前に `pip install libkuraji[integration]` を実行して `fugashi` をインストールしてください。

```python
import libkuraji

# MeCabとJTalk拡張辞書を自動でダウンロード・セットアップして翻訳
cells, inpos, outpos, cursor = libkuraji.translate_kanji("私は点字を読みます")
# => '⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲'
```

カスタムの解析器（形態素解析器）を使用する場合は、`initialize` で明示的に注入できます。

```python
import libkuraji

# analyzer には analyze(text, logwrite) と is_ready() を持つオブジェクトを指定します
libkuraji.initialize(analyzer=my_analyzer)
cells, inpos, outpos, cursor = libkuraji.translate_kanji("私は点字を読みます")
```

### CLI

```console
# カナ入力（依存パッケージ不要で実行可能）
$ kuraji "ワタシワ テンジヲ ヨミマス。"
⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲

# 漢字交じり入力（[integration] がインストールされている場合、自動で実辞書を使用して翻訳）
$ kuraji "私は点字を読みます。"
⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲

# 位置対応マップ（JSON形式）を合わせて出力
$ kuraji "ア" --positions
{"text": "ア", "braille": "⠁", "inPos": [0], "outPos": [0]}
```

## テスト

```console
pip install -e .[dev]
pytest
```

テストデータ `tests/harness.json` 等は点訳のてびきの規則に基づくテストケース集です。`tests/mecabFixture.json` は参照構成の MeCab 出力の録画で、translator2 のテストを MeCab なしで再生します（再録画は nvdajp リポジトリの `miscDepsJp/jptools/recordMecabFixture.py`）。

### 実辞書を使った統合テスト（任意）

通常のテストは MeCab を使わない録画ベースです。さらに、実際の JTalk 拡張辞書を使ったテストランナーを opt-in で走らせることができます。

事前要件:

- `pip install -e .[integration]`（`fugashi` が入ります。Windows の場合は `libmecab.dll` も同梱されるため、MeCab ランタイムの別途用意は不要です）
- `gh` CLI（未導入なら GitHub REST API にフォールバック）

実行:

```console
pip install -e .[dev,integration]
$env:LIBKURAJI_INTEGRATION=1
pytest tests/test_integration.py -q

# （オプション）MeCab出力の完全一致チェック（パリティテスト）も実行する場合
$env:LIBKURAJI_PARITY_CHECK=1
pytest tests/test_integration.py -q
```

辞書バイナリは [libkuraji-jtalk-dic](https://github.com/nishimotz/libkuraji-jtalk-dic) の GitHub Release から取得します。取得するタグは `LIBKURAJI_JTALK_DIC_TAG` で上書き可能（既定値は `src/libkuraji/jtalk_dic.py` の `DEFAULT_DIC_TAG` に pin されています）。展開済み辞書ディレクトリを直接指定する場合は `LIBKURAJI_JTALK_DIC_DIR` を使ってください（その場合はダウンロードをスキップします）。

この統合テストの一部（点訳・分かち書きの整合性検証）は、CI（GitHub Actions）の Windows および Linux 環境でも自動実行されるようになっています。ただし、MeCab本体のバージョン差による内部的なトークン・フィーチャー出力の差異（`test_mecab_fixture_parity`）は、辞書アップデート時などの差分検証用テストであるため、デフォルトでスキップされます（実行するには `LIBKURAJI_PARITY_CHECK=1` を指定します）。

実行には `pip install -e .[dev,integration]` で `fugashi` を導入します。`fugashi` の Windows wheel は `libmecab.dll` を同梱しているため、**Windows でも pip だけで完結します**（`libmecab` のシステムインストールは不要）。

統合テストは `mecab_correct.py`（元 nvdajp の `Mecab_correctFeatures` を BSD 再許諾のうえ移管）で MeCab 出力の補正も再現しています。ただし、`fugashi` 同梱の `libmecab.dll` と fixture 録画時に使った nvdajp 版 MeCab で未知語（記号）の分割挙動に差があるため、記号のみの入力など少数ケースで fixture と一致しません（全体の約 98% は一致）。この MeCab 本体の挙動の違いによる内部出力の差分は CI では無視されますが、点訳の最終出力の整合性は完全に維持されており、CI も Green でパスする構成になっています。

## NVDA 日本語版との関係

- 本ライブラリは [nvdajp](https://github.com/nvdajp/nvdajp) の点訳エンジン（translator1/translator2）を分離・独立させたものです。translator1 相当（`kana` モジュール）はテスト駆動で新規に書き直したクリーンルーム実装、translator2 は著作権者による BSD 再許諾のうえ移管しました。
- 分離計画の詳細: nvdajp の `projectDocs/jp/braille-engine-decoupling-plan.md`

## ライセンス

BSD 3-Clause License. See [LICENSE](LICENSE).
