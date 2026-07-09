# 点字出力の文字コード

[English](encoding.md)

libkuraji は点字セルを 2 通りの文字コードで返せます。`translate_kanji` の `unicodeIO` 引数は、liblouis の `ucBrl`（Unicode Braille）フラグに相当する切り替えです。

## Unicode 点字（推奨）

| 項目 | 値 |
|------|-----|
| 点字セル | [Unicode Braille Patterns](https://www.unicode.org/charts/PDF/U2800.pdf) `U+2800`..`U+28FF` |
| 空白（マスあけ） | `U+0020` SPACE |
| 有効にする方法 | `translate_kanji(..., unicodeIO=True)` |
| liblouis 対応 | `dotsIO` + `ucBrl` |
| CLI | 常にこの形式で出力 |

例: `ア` → `⠁` (`U+2801`)

新規の利用コードでは、この形式を使うことを推奨します。CLI の出力とも一致します。

## liblouis dotsIO 表現（既定）

| 項目 | 値 |
|------|-----|
| 点字セル | Private Use Area `U+8000`..`U+80FF` |
| 空白（マスあけ） | `U+2800` BRAILLE PATTERN BLANK |
| 既定値 | `translate_kanji` の `unicodeIO` 省略時（`False`） |
| liblouis 対応 | `dotsIO` のみ（`ucBrl` なし） |

liblouis が「dot patterns」として内部表現する形式です。`translator2.translate()` は nvdajp 由来の liblouis 互換 API であり、コメントにも `mode=dotsIO is default` とあります（`src/libkuraji/translator2.py`）。libkuraji として NVDA 専用に設計したモードではなく、移管コードの既定値がそのまま残っています。

NVDA 日本語版がこの形式を使っていたのは、スクリーンリーダー側が liblouis / translator2 互換の出力を前提にしていたためです。

### 変換規則

内部ではまず Unicode 点字（空白は `U+0020`）として組み立て、その後 `unicodeIO=False` のとき次の変換を行います。

1. 空白 `U+0020` を `U+2800` に置換
2. 各文字 `c` について `chr((ord(c) - 0x2800) + 0x8000)` を出力

逆変換（dotsIO → Unicode）は `chr(ord(c) - 0x8000 + 0x2800)` です（`U+8000` は空白セル）。

外国語引用符内の liblouis 2 級変換でも、`_apply_louis_to_foreign_quotes` は `louis.dotsIO` モードで呼び出し、返り値を `_louis_cells_to_braille_string` で Unicode 点字に正規化してから `outbuf` に統合します。

## API ごとの既定値

| API | 出力形式 | 備考 |
|-----|----------|------|
| `translate` / `translate_with_pos` | Unicode 点字 | カナ入力専用（`kana` モジュール） |
| `translate_kanji` | dotsIO（`unicodeIO=False`） | nvdajp translator2 由来の既定。`unicodeIO=True` で Unicode 点字 |
| `kuraji`（CLI） | Unicode 点字 | 内部で `unicodeIO=True` を指定 |

## 実装上の参照

- dotsIO 変換: `src/libkuraji/translator2.py` の `translate()`（`unicodeIO` 引数）
- liblouis 呼び出し: 同ファイルの `_apply_louis_to_foreign_quotes`（`mode=louis.dotsIO`）
- カナ点字の Unicode 出力: `src/libkuraji/kana.py`
- CLI: `src/libkuraji/cli.py`（`unicodeIO=True` 固定）
