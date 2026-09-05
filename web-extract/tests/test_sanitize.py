#!/usr/bin/env python3
"""Unit tests for web-fetch.py's sanitize() and absolutize().

Run: python3 tests/test_sanitize.py    (stdlib only, no test framework, exit 0 = pass)

These cover the one piece of genuinely security-relevant logic in the plugin, and nothing
else exercises it: no backend currently in the ladder leaks invisible Unicode, so sanitize()
would otherwise ship untested. That is exactly the situation these tests exist to prevent —
a boundary guarantee nobody has checked is not a guarantee.

The joiner cases are the ones to be careful with. ZWJ/ZWNJ must survive in emoji sequences
and Persian/Arabic orthography while being stripped between ASCII characters. Breaking that
distinction silently corrupts real content, so both directions are asserted.
"""
import importlib.util
import pathlib
import sys

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "web-fetch.py"
spec = importlib.util.spec_from_file_location("webfetch", SCRIPT)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)

fails = []


def check(name, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}")
    if not ok:
        print(f"        got:  {got!r}")
        print(f"        want: {want!r}")
        fails.append(name)


def san(text):
    return wf.sanitize(text, "test")


print("--- sanitize: strips invisible injection channels ---")
check("unicode tag chars removed", san("hi\U000E0028\U000E0029there"), "hithere")
check("bidi override removed", san("safe‮evil‬end"), "safeevilend")
check("zero-width space removed", san("in​visible"), "invisible")
check("word joiner removed", san("a⁠b"), "ab")
check("BOM removed", san("﻿start"), "start")
check("soft hyphen removed", san("soft­hyphen"), "softhyphen")

print("\n--- sanitize: preserves legitimate joiners ---")
check("ZWJ in emoji family preserved",
      san("\U0001F468‍\U0001F469"), "\U0001F468‍\U0001F469")
check("ZWNJ in Persian preserved", san("ک‌ا"), "ک‌ا")
check("variation selector preserved", san("❤️"), "❤️")

print("\n--- sanitize: strips joiners only where they cannot be orthographic ---")
check("ZWJ between ASCII removed", san("ig‍nore"), "ignore")
check("ZWNJ between ASCII removed", san("ig‌nore"), "ignore")

print("\n--- sanitize runs before classify: signature evasion is defeated ---")
# Exactly one marker present, and it is zero-width padded. Nothing else can match.
evaded = "Please wait. Ray​ ID: 8ab3f. Contact the site owner for help."
check("un-sanitised: padded marker evades detection entirely",
      wf.matched_marker(evaded), None)
check("un-sanitised: would have been returned as content", wf.classify(evaded), "thin")
check("sanitised: marker matches again", wf.matched_marker(san(evaded)), "ray id:")
check("sanitised: page correctly classifies blocked", wf.classify(san(evaded)), "blocked")

print("\n--- absolutize ---")
B = "https://example.com/docs/guide.html"
check("root-relative resolved", wf.absolutize("[a](/x/y)", B), "[a](https://example.com/x/y)")
check("path-relative resolved", wf.absolutize("[a](sub/z)", B),
      "[a](https://example.com/docs/sub/z)")
check("absolute untouched", wf.absolutize("[a](https://other.org/p)", B),
      "[a](https://other.org/p)")
check("anchor untouched", wf.absolutize("[a](#sec)", B), "[a](#sec)")
check("mailto untouched", wf.absolutize("[a](mailto:x@y.z)", B), "[a](mailto:x@y.z)")
check("image links resolved", wf.absolutize("![alt](/img/a.png)", B),
      "![alt](https://example.com/img/a.png)")
check("link with title preserved", wf.absolutize('[a](/p "T")', B),
      '[a](https://example.com/p "T")')

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
