#!/usr/bin/env python3
"""Normalize decorative Unicode symbols in Python source files to ASCII equivalents.

Targets: .py files under app/, excluding UI/web bundles where visual symbols may be intended.
Creates a .bak backup for each modified file.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = [
    ROOT / "ui",
    ROOT / "web",
    ROOT / "bundle_tmp",
    ROOT / "archive",
]

REPLACEMENTS = {
    "OK:": "OK:",
    "OK:": "OK:",
    "FAIL:": "FAIL:",
    "FAIL:": "FAIL:",
    "WARN:": "WARN:",
    "WARN:": "WARN:",
    "...": "...",
}


def is_excluded(p: Path) -> bool:
    for d in EXCLUDE_DIRS:
        try:
            if d in p.parents:
                return True
        except Exception:
            continue
    return False


changed = []
for p in ROOT.rglob("*.py"):
    if is_excluded(p):
        continue
    text = p.read_text(encoding="utf-8")
    new = text
    for k, v in REPLACEMENTS.items():
        if k in new:
            new = new.replace(k, v)
    if new != text:
        bak = p.with_suffix(p.suffix + ".bak")
        bak.write_text(text, encoding="utf-8")
        p.write_text(new, encoding="utf-8")
        changed.append(str(p.relative_to(ROOT)))

print("Modified files:")
for c in changed:
    print(" -", c)
print(f"Total modified: {len(changed)}")
