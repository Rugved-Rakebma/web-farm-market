#!/usr/bin/env python3
"""Report invisible/format codepoints present in a file, grouped by class."""
import sys
import unicodedata

CLASSES = {
    "TAG CHARS (U+E0000-E007F)": lambda c: 0xE0000 <= ord(c) <= 0xE007F,
    "BIDI OVERRIDE/ISOLATE": lambda c: ord(c) in set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)),
    "ZERO WIDTH SPACE U+200B": lambda c: ord(c) == 0x200B,
    "ZWNJ U+200C": lambda c: ord(c) == 0x200C,
    "ZWJ U+200D": lambda c: ord(c) == 0x200D,
    "WORD JOINER U+2060": lambda c: ord(c) == 0x2060,
    "BOM/ZWNBSP U+FEFF": lambda c: ord(c) == 0xFEFF,
    "SOFT HYPHEN U+00AD": lambda c: ord(c) == 0x00AD,
    "OTHER Cf (format)": lambda c: unicodedata.category(c) == "Cf",
}

text = open(sys.argv[1], encoding="utf-8").read()
seen = {}
for ch in text:
    for name, test in CLASSES.items():
        if test(ch):
            seen.setdefault(name, []).append(ch)
            break

if not seen:
    print("  (none)")
for name, chars in seen.items():
    pts = " ".join(sorted({f"U+{ord(c):04X}" for c in chars}))
    print(f"  {len(chars):3d}x  {name}  [{pts}]")
