import json
from pathlib import Path
from typing import Dict, Set

path = Path("ruff-report-after.json")
if not path.exists():
    print("No JSON report found or empty.")
else:
    rep = json.loads(path.read_text(encoding="utf-8"))
    byfile: Dict[str, Set[str]] = {}
    for entry in rep:
        path_name = entry.get("filename") or entry.get("path")
        code = entry.get("code")
        if not path_name or not code:
            continue
        byfile.setdefault(path_name, set()).add(code)
    for path_name in sorted(byfile):
        codes = ",".join(sorted(byfile[path_name]))
        print(f"{path_name}: {codes}")
