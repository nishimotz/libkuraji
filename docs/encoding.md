# Braille output encoding

[日本語](encoding-ja.md)

libkuraji can return braille cells in two encodings. The `unicodeIO` argument to `translate_kanji` corresponds to liblouis's `ucBrl` (Unicode Braille) flag.

## Unicode braille (recommended)

| Item | Value |
|------|-------|
| Braille cells | [Unicode Braille Patterns](https://www.unicode.org/charts/PDF/U2800.pdf) `U+2800`..`U+28FF` |
| Blank (masuake) | `U+0020` SPACE |
| How to enable | `translate_kanji(..., unicodeIO=True)` |
| liblouis equivalent | `dotsIO` + `ucBrl` |
| CLI | Always uses this format |

Example: `ア` → `⠁` (`U+2801`)

Use this format in new code. It matches CLI output.

## liblouis dotsIO representation (default)

| Item | Value |
|------|-------|
| Braille cells | Private Use Area `U+8000`..`U+80FF` |
| Blank (masuake) | `U+2800` BRAILLE PATTERN BLANK |
| Default | `translate_kanji` with `unicodeIO` omitted (`False`) |
| liblouis equivalent | `dotsIO` only (no `ucBrl`) |

This is liblouis's internal "dot patterns" representation. `translator2.translate()` is a liblouis-compatible API ported from nvdajp; its source comments state `mode=dotsIO is default` (`src/libkuraji/translator2.py`). libkuraji did not design this as an NVDA-specific mode—the default is inherited from the ported code.

NVDA Japanese used this format because the screen reader expected liblouis / translator2 compatible output.

### Conversion rules

Internally, braille is built as Unicode braille (blanks as `U+0020`). When `unicodeIO=False`, the following conversion is applied:

1. Replace blank `U+0020` with `U+2800`
2. For each character `c`, output `chr((ord(c) - 0x2800) + 0x8000)`

The reverse conversion (dotsIO → Unicode) is `chr(ord(c) - 0x8000 + 0x2800)` (`U+8000` is a blank cell).

### Grade 2 translation inside foreign quotation marks (reference)

`_apply_louis_to_foreign_quotes` performs Grade 2 translation on the inner text of foreign quotation marks `⠦...⠴` **only when the caller injects** a `louisTranslate` function and `louisTableList`. libkuraji itself does not provide a `louis` translate function — this feature is an external dependency.

When injected, it calls liblouis with `louis.dotsIO` mode, then normalizes the result to Unicode braille via `_louis_cells_to_braille_string` before merging into `outbuf`.

Information processing braille `⠠⠦...⠠⠴` (URLs, email addresses, file paths, etc.) is excluded from Grade 2 translation. `_find_foreign_quote_ranges` explicitly skips ranges prefixed with `⠠`.

## Defaults by API

| API | Output format | Notes |
|-----|---------------|-------|
| `translate` / `translate_with_pos` | Unicode braille | Kana input only (`kana` module) |
| `translate_kanji` | dotsIO (`unicodeIO=False`) | Inherited from nvdajp translator2. Use `unicodeIO=True` for Unicode braille |
| `kuraji` (CLI) | Unicode braille | Passes `unicodeIO=True` internally |

## Implementation references

- dotsIO conversion: `translate()` in `src/libkuraji/translator2.py` (`unicodeIO` argument)
- liblouis calls: `_apply_louis_to_foreign_quotes` in the same file (`mode=louis.dotsIO`)
- Unicode kana braille: `src/libkuraji/kana.py`
- CLI: `src/libkuraji/cli.py` (`unicodeIO=True` fixed)
