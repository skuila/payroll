#!/usr/bin/env python3
"""
Safe fixes:
- Split lines like 'import a, b' into separate import lines.
- Replace bare 'except:' with 'except Exception as _exc:' (underscore to avoid unused-var warning).
Works only on .py under app/. Makes backups *.bak before changing.
"""
import re
from pathlib import Path
import shutil

files = list(Path("app").rglob("*.py"))
print(f"Found {len(files)} python files under app/")

for f in files:
    text = f.read_text(encoding="utf-8")
    orig = text
    changed = False
    bak = f.with_suffix(f.suffix + ".bak")
    if not bak.exists():
        shutil.copy(f, bak)
    lines = text.splitlines()
    out_lines = []
    for line in lines:
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        m = re.match(r"^(\s*)import\s+(.+)", line)
        if m and "from " not in line:
            rest = m.group(2)
            if "," in rest and "(" not in rest and ")" not in rest:
                parts = [p.strip() for p in rest.split(",")]
                comment = ""
                if parts and "#" in parts[-1]:
                    last = parts[-1]
                    ppart, _, cmt = last.partition("#")
                    parts[-1] = ppart.strip()
                    comment = "#" + cmt
                for i, part in enumerate(parts):
                    if not part:
                        continue
                    suffix = " " + comment if (i == len(parts) - 1 and comment) else ""
                    out_lines.append(f"{indent}import {part}{suffix}")
                changed = True
                continue
        if re.match(r"^\s*except\s*:\s*(#.*)?$", line):
            trailing = ""
            if "#" in line:
                trailing = " " + line.split("#", 1)[1].rstrip()
            out_lines.append(f"{indent}except Exception as _exc:{trailing}")
            changed = True
            continue
        out_lines.append(line)
    new_text = "\n".join(out_lines)
    if text.endswith("\n"):
        new_text += "\n"
    if changed and new_text != orig:
        f.write_text(new_text, encoding="utf-8")
        print(f"Patched {f}")
print("Safe fixes complete. Backups saved as *.bak under each file.")
