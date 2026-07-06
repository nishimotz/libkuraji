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

### CLI

```console
$ kuraji "ワタシワ テンジヲ ヨミマス。"
⠄⠕⠳⠄ ⠟⠴⠐⠳⠔ ⠜⠷⠵⠹⠲
$ echo テキスト | kuraji
$ kuraji --nabcc "ガイド(U)"
```

### 分かち書きパイプライン（translator2）

漢字かな交じり文からの点訳には形態素解析器の注入が必要です。

```python
from libkuraji import translator2

translator2.initialize(analyzer=my_analyzer)
kana, cells, inpos1, inpos2 = translator2.translateWithInPos2("私は点字を読みます")
```

`analyzer` に必要なインターフェースは次の 2 つです。

- `analyze(text, logwrite) -> list[str]` — MeCab 形式のデコード済み feature 行を返す
- `is_ready() -> bool`

参照構成（テストスイートが保証する構成）は **MeCab + JTalk 拡張辞書**（NVDA 日本語版の `mecabAnalyzer.py`）です。feature 行の第 13 フィールド（点訳表記）はこの辞書の拡張仕様で、無い場合は読みフィールドにフォールバックします。汎用辞書（mecab-python3 + ipadic 等）の注入も可能ですが、読み・分かち書きの品質は保証外です。

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
```

辞書バイナリは [libkuraji-jtalk-dic](https://github.com/nishimotz/libkuraji-jtalk-dic) の GitHub Release から取得します。取得するタグは `LIBKURAJI_JTALK_DIC_TAG` で上書き可能（既定値は `src/libkuraji/jtalk_dic.py` の `DEFAULT_DIC_TAG` に pin されています）。展開済み辞書ディレクトリを直接指定する場合は `LIBKURAJI_JTALK_DIC_DIR` を使ってください（その場合はダウンロードをスキップします）。

この統合テストの一部（点訳・分かち書きの整合性検証）は、CI（GitHub Actions）の Windows 環境でも自動実行されるようになっています。ただし、MeCab本体のバージョン差による内部的なトークン・フィーチャー出力の差異（`test_mecab_fixture_parity`）は CI の実行対象から除外されています。

実行には `pip install -e .[dev,integration]` で `fugashi` を導入します。`fugashi` の Windows wheel は `libmecab.dll` を同梱しているため、**Windows でも pip だけで完結します**（`libmecab` のシステムインストールは不要）。

統合テストは `mecab_correct.py`（元 nvdajp の `Mecab_correctFeatures` を BSD 再許諾のうえ移管）で MeCab 出力の補正も再現しています。ただし、`fugashi` 同梱の `libmecab.dll` と fixture 録画時に使った nvdajp 版 MeCab で未知語（記号）の分割挙動に差があるため、記号のみの入力など少数ケースで fixture と一致しません（全体の約 98% は一致）。この MeCab 本体の挙動の違いによる内部出力の差分は CI では無視されますが、点訳の最終出力の整合性は完全に維持されており、CI も Green でパスする構成になっています。

## NVDA 日本語版との関係

- 本ライブラリは [nvdajp](https://github.com/nvdajp/nvdajp) の点訳エンジン（translator1/translator2）を分離・独立させたものです。translator1 相当（`kana` モジュール）はテスト駆動で新規に書き直したクリーンルーム実装、translator2 は著作権者による BSD 再許諾のうえ移管しました。
- 分離計画の詳細: nvdajp の `projectDocs/jp/braille-engine-decoupling-plan.md`

## ライセンス

BSD 3-Clause License. See [LICENSE](LICENSE).
