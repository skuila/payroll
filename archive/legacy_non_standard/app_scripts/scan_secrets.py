"""Simple scanner to find likely secrets in the repository.
Usage: python scripts/scan_secrets.py [path]
Prints files and matching lines for a set of secret-like patterns.
"""

import sys
import re
from pathlib import Path

PATTERNS = [
    re.compile(r"(?i)password\s*=\s*[^\n]+"),
    re.compile(r"(?i)pwd\s*=\s*[^\n]+"),
    re.compile(r"(?i)pass(word|phrase)"),
    re.compile(r"(?i)postgresql://[^\s\']+:[^@\s]+@"),
    re.compile(r"(?i)aq456"),
]


def scan(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix not in {".pyc", ".exe", ".dll"}:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                for pat in PATTERNS:
                    if pat.search(line):
                        print(f"{p}:{i}: {line.strip()}")
                        break


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent
    print(f"Scanning {root} ...")
    scan(root)
