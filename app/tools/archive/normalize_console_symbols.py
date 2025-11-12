#!/usr/bin/env python3
"""ARCHIVE: normalize_console_symbols.py

Cette copie est archivée dans `app/tools/archive/` après demande d'archivage
et suppression de la version active. Conserve le script original pour référence.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDE_DIRS = [
    ROOT / "ui",
    ROOT / "web",
    ROOT / "bundle_tmp",
    ROOT / "archive",
]

REPLACEMENTS = {
    "OK:": "OK:",
    "FAIL:": "FAIL:",
    "WARN:": "WARN:",
}


def is_excluded(p: Path) -> bool:
    for d in EXCLUDE_DIRS:
        try:
            if d in p.parents:
                return True
        except Exception:
            continue
    return False


def main():
    print("ARCHIVE copy of normalize_console_symbols.py")


if __name__ == "__main__":
    main()
